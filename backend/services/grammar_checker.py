"""Spelling and writing-style checks tuned for resumes.

A general-purpose grammar checker is the wrong tool here. Resume bullets are
deliberate sentence fragments with no articles and no subject, so a
conventional checker floods the output with false positives on text that is
correctly written for its genre.

So this module does two things instead:

1. **Spelling**, filtered hard. A checker that flags `FastAPI` or `PostgreSQL`
   is worse than no checker at all — it teaches the user to ignore it. Tokens
   are only checked when they look like ordinary prose words (see `_is_checkable`).
2. **Resume-specific style rules** — first-person pronouns, weak bullet openers,
   duplicated words — which are what actually costs a candidate a screen.

The returned dict matches `get_default_grammar_results()` exactly, so the
scorer neither knows nor cares whether a real check ran.
"""

import logging
import re
from typing import Dict, Iterable, List, Optional, Set

logger = logging.getLogger('ats_resume_scorer')

try:
    from spellchecker import SpellChecker

    _SPELLCHECKER_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only in stripped installs
    SpellChecker = None  # type: ignore[assignment]
    _SPELLCHECKER_AVAILABLE = False
    logger.warning('pyspellchecker not installed — spelling checks disabled')

# Penalty weight per severity. The total feeds _calc_content_score as
# `10 - penalty/2`, so 20 points of penalty zeroes that part of the score.
_WEIGHTS = {'critical': 1.5, 'moderate': 1.0, 'minor': 0.25}
_MAX_PENALTY = 20.0

# Entity labels whose text is a name, not a word to be spell-checked.
_NAME_ENTITIES = frozenset(
    {'PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT', 'FAC', 'NORP', 'EVENT', 'LANGUAGE', 'WORK_OF_ART'}
)

# Technology and resume vocabulary a general dictionary doesn't carry.
# Anything camelCase or ALL-CAPS is already skipped, so this is only for terms
# that are legitimately written lowercase.
_TECH_TERMS = frozenset({
    'api', 'apis', 'backend', 'frontend', 'fullstack', 'middleware', 'runtime',
    'framework', 'frameworks', 'kubernetes', 'docker', 'redis', 'kafka', 'nginx',
    'postgres', 'postgresql', 'mysql', 'sqlite', 'mongodb', 'dynamodb', 'firebase',
    'python', 'javascript', 'typescript', 'golang', 'kotlin', 'scala', 'rust',
    'django', 'flask', 'fastapi', 'numpy', 'pandas', 'pytorch', 'tensorflow',
    'keras', 'sklearn', 'matplotlib', 'jupyter', 'anaconda', 'linux', 'ubuntu',
    'terraform', 'ansible', 'jenkins', 'gitlab', 'github', 'bitbucket', 'devops',
    'microservices', 'microservice', 'serverless', 'kubernetes', 'grafana',
    'prometheus', 'elasticsearch', 'rabbitmq', 'graphql', 'websocket', 'websockets',
    'oauth', 'jwt', 'json', 'yaml', 'html', 'css', 'sass', 'tailwind', 'bootstrap',
    'webpack', 'vite', 'npm', 'yarn', 'pnpm', 'eslint', 'pytest', 'unittest',
    'scalable', 'scalability', 'observability', 'onboarding', 'upsell',
    'analytics', 'dataset', 'datasets', 'dataframe', 'workflow', 'workflows',
    'roadmap', 'stakeholder', 'stakeholders', 'kpi', 'kpis', 'saas', 'ecommerce',
    'chatbot', 'realtime', 'multithreading', 'async', 'refactored', 'refactoring',
    'cicd', 'repo', 'repos', 'sdk', 'cli', 'ui', 'ux', 'crud', 'orm', 'llm', 'llms',
})

# First-person pronouns. Resumes are written in an implied first person; making
# it explicit reads as unpolished and wastes line width.
_FIRST_PERSON = re.compile(r'\b(I|me|my|mine|myself|we|our|ours)\b')

# Bullet openers that describe duties rather than achievements.
_WEAK_OPENERS = [
    'responsible for', 'worked on', 'helped with', 'helped to', 'assisted with',
    'assisted in', 'duties included', 'involved in', 'tasked with', 'in charge of',
    'was responsible', 'participated in',
]

_REPEATED_WORD = re.compile(r'\b(\w+)\s+\1\b', re.IGNORECASE)
_DOUBLE_SPACE = re.compile(r'\S {2,}\S')
_SPACE_BEFORE_PUNCT = re.compile(r'\s+([,.;:!?])')
_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
_URL_OR_EMAIL = re.compile(
    r'\S+@\S+'                                          # emails
    r'|https?://\S+'                                     # absolute URLs
    r'|www\.\S+'                                         # www-prefixed
    r'|\S+\.(?:com|org|net|io|dev|ai|co|edu|gov)\S*'    # bare domains AND their paths
)
_BULLET = re.compile(r'^\s*[•◦\-\*●▪]\s*|^\s*\d+[.)]\s*')


# British → American transformations. A word is accepted when any variant is
# in the dictionary, so `containerised` and `optimised` aren't flagged as typos.
_BRITISH_SUFFIXES = [
    ('isation', 'ization'), ('isations', 'izations'),
    ('ising', 'izing'), ('ised', 'ized'), ('ises', 'izes'), ('ise', 'ize'),
    ('yse', 'yze'), ('ysed', 'yzed'), ('ysing', 'yzing'),
    ('ogue', 'og'), ('ogues', 'ogs'),
    ('our', 'or'), ('ours', 'ors'), ('oured', 'ored'), ('ouring', 'oring'),
    ('re', 'er'), ('res', 'ers'),
    ('lled', 'led'), ('lling', 'ling'), ('ller', 'ler'),
    ('ence', 'ense'), ('ences', 'enses'),
]


def _americanised(word: str) -> Iterable[str]:
    """Yield plausible US spellings of a British-spelled word."""
    for british, american in _BRITISH_SUFFIXES:
        if word.endswith(british):
            yield word[: -len(british)] + american


def _error(text: str, message: str, suggestions: Optional[List[str]] = None, context: str = '') -> Dict:
    return {
        'error_text': text,
        'message': message,
        'suggestions': suggestions or [],
        'context': context.strip()[:120],
    }


def _is_checkable(token: str) -> bool:
    """True when a token looks like ordinary prose worth spell-checking.

    Everything that looks like a technology, an acronym, a name or an
    identifier is skipped — false positives there are far more damaging than
    the misspellings they'd catch.
    """
    if len(token) < 4:
        return False
    if any(char.isdigit() for char in token):
        return False
    # camelCase / PascalCase (FastAPI, PostgreSQL, JavaScript) — a product name.
    if any(char.isupper() for char in token[1:]):
        return False
    # ALL-CAPS acronyms are caught by the rule above only when len > 1, so this
    # covers the remainder.
    if token.isupper():
        return False
    if not token.isalpha():
        return False
    return token.lower() not in _TECH_TERMS


def _entity_words(text: str, nlp) -> Set[str]:
    """Lowercased words belonging to named entities — names, not misspellings."""
    if nlp is None:
        return set()
    try:
        doc = nlp(text[:100_000])
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(f'spaCy failed during grammar check: {exc}')
        return set()

    words: Set[str] = set()
    for ent in doc.ents:
        if ent.label_ in _NAME_ENTITIES:
            words.update(part.lower() for part in _WORD.findall(ent.text))
    return words


def _check_spelling(text: str, skip: Set[str]) -> List[Dict]:
    if not _SPELLCHECKER_AVAILABLE:
        return []

    checker = SpellChecker()
    candidates = {
        token for token in _WORD.findall(_URL_OR_EMAIL.sub(' ', text))
        if _is_checkable(token) and token.lower() not in skip
    }
    if not candidates:
        return []

    lowered = {token.lower(): token for token in candidates}
    misspelled = checker.unknown(lowered.keys())

    errors = []
    for word in sorted(misspelled):
        # A British spelling is not a misspelling.
        if any(variant not in checker.unknown([variant]) for variant in _americanised(word)):
            continue
        original = lowered.get(word, word)
        correction = checker.correction(word)
        suggestions = [correction] if correction and correction != word else []
        errors.append(
            _error(
                original,
                f"'{original}' looks misspelled.",
                suggestions,
            )
        )
    return errors


def _iter_bullets(text: str) -> Iterable[str]:
    for line in text.split('\n'):
        if _BULLET.match(line):
            stripped = _BULLET.sub('', line).strip()
            if stripped:
                yield stripped


def _check_style(text: str) -> tuple[List[Dict], List[Dict]]:
    """Returns (moderate, minor) style findings."""
    moderate: List[Dict] = []
    minor: List[Dict] = []

    # First-person pronouns.
    seen_pronouns: Set[str] = set()
    for line in text.split('\n'):
        for match in _FIRST_PERSON.finditer(line):
            word = match.group(1).lower()
            if word in seen_pronouns:
                continue
            seen_pronouns.add(word)
            moderate.append(
                _error(
                    match.group(1),
                    f"Avoid first-person pronouns — drop '{match.group(1)}' and lead with a verb.",
                    context=line,
                )
            )

    # Weak bullet openers.
    for bullet in _iter_bullets(text):
        lowered = bullet.lower()
        for opener in _WEAK_OPENERS:
            if lowered.startswith(opener):
                moderate.append(
                    _error(
                        opener,
                        f"'{bullet[:len(opener)]}' describes a duty, not an achievement. "
                        'Start with a past-tense action verb instead.',
                        context=bullet,
                    )
                )
                break

    # Duplicated words.
    for match in _REPEATED_WORD.finditer(text):
        moderate.append(
            _error(
                match.group(0),
                f"Repeated word: '{match.group(0)}'.",
                [match.group(1)],
                context=match.group(0),
            )
        )

    # Spacing and punctuation nits.
    if _DOUBLE_SPACE.search(text):
        count = len(_DOUBLE_SPACE.findall(text))
        minor.append(
            _error('  ', f'{count} instance(s) of doubled spaces — tidy these up.')
        )

    for match in _SPACE_BEFORE_PUNCT.finditer(text):
        minor.append(
            _error(
                match.group(0),
                f"Space before '{match.group(1)}' — remove it.",
            )
        )
        if len(minor) > 5:
            break

    # Bullets that don't start with a capital letter.
    lowercase_bullets = [b for b in _iter_bullets(text) if b[0].islower()]
    if lowercase_bullets:
        minor.append(
            _error(
                lowercase_bullets[0][:40],
                f'{len(lowercase_bullets)} bullet(s) start with a lowercase letter — '
                'capitalise the first word of each.',
                context=lowercase_bullets[0],
            )
        )

    return moderate, minor


def check_grammar(text: str, nlp=None, known_skills: Optional[Iterable[str]] = None) -> Dict:
    """Run spelling and style checks over the resume text.

    `known_skills` comes from the LLM-parsed resume; those words are always
    treated as correctly spelled, since they're the candidate's own vocabulary.
    """
    if not text or not text.strip():
        from backend.utils.file_utils import get_default_grammar_results

        return get_default_grammar_results()

    skip = {word.lower() for skill in (known_skills or []) for word in _WORD.findall(str(skill))}
    skip |= _entity_words(text, nlp)

    critical = _check_spelling(text, skip)
    moderate, minor = _check_style(text)

    total = len(critical) + len(moderate) + len(minor)
    penalty = min(
        _MAX_PENALTY,
        len(critical) * _WEIGHTS['critical']
        + len(moderate) * _WEIGHTS['moderate']
        + len(minor) * _WEIGHTS['minor'],
    )

    word_count = len(_WORD.findall(text)) or 1
    error_free_pct = round(max(0.0, 100.0 * (1 - total / word_count)), 1)

    return {
        'total_errors': total,
        'critical_errors': critical,
        'moderate_errors': moderate,
        'minor_errors': minor,
        'grammar_score': round(max(0.0, 100.0 - penalty * 5), 1),
        'penalty_applied': round(penalty, 2),
        'error_free_percentage': error_free_pct,
        '_component_status': 'ok' if _SPELLCHECKER_AVAILABLE else 'partial',
        '_note': (
            'Spelling and resume style checked.'
            if _SPELLCHECKER_AVAILABLE
            else 'Style checked; spelling unavailable (pyspellchecker not installed).'
        ),
    }
