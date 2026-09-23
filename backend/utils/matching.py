import re
from typing import Dict, Iterable, List

from rapidfuzz import fuzz

SKILL_ALIASES: Dict[str, str] = {
    'reactjs':       'react',
    'react.js':      'react',
    'angularjs':     'angular',
    'vuejs':         'vue',
    'vue.js':        'vue',
    'nextjs':        'next.js',
    'nodejs':        'node.js',
    'node':          'node.js',
    'expressjs':     'express',
    'express.js':    'express',
    'springboot':    'spring boot',
    'golang':        'go',
    'ml':            'machine learning',
    'ai':            'artificial intelligence',
    'nlp':           'natural language processing',
    'cv':            'computer vision',
    'k8s':           'kubernetes',
    'sklearn':       'scikit-learn',
    'postgres':      'postgresql',
    'dotnet':        '.net',
    'tailwindcss':   'tailwind',
    'amazon web services': 'aws',
    'google cloud':  'gcp',
    'pyspark':       'spark',
    'huggingface':   'hugging face',
}


# ── Keyword hygiene ─────────────────────────────────────────────────────────
# An LLM asked for "keywords" will sometimes return requirement sentences:
#
#   "Bachelor's degree in Statistics, Mathematics, Machine Learning, ..."
#   "1-3 years experience with insurance claims and EHR databases (e.g., IQVIA)"
#
# Those can never fuzzy-match a resume term, so every one inflates the missing
# count — which drives the score penalty. Left unfiltered they make a resume
# look like it matches almost nothing.
#
# spaCy noun chunks have the mirror problem: "a growth mindset", "a series",
# "a related field" are grammatical noun phrases but useless as skills.

_MAX_KEYWORD_WORDS = 4
_MAX_KEYWORD_CHARS = 40

# Sentence punctuation, list separators and prose markers. A keyword has none.
_PROSE_MARKERS = re.compile(r'[(),;:]|e\.g\.|i\.e\.|etc', re.IGNORECASE)

# Leading words that make a noun phrase rather than a skill.
_LEADING_NOISE = frozenset({
    'a', 'an', 'the', 'this', 'that', 'these', 'those', 'any', 'all', 'some',
    'your', 'our', 'their', 'its', 'his', 'her', 'my',
    'other', 'related', 'various', 'several', 'such', 'each', 'every', 'both',
})

# Phrases that are requirements or boilerplate, not skills.
_BOILERPLATE = frozenset({
    'years', 'year', 'experience', 'degree', 'field', 'ability', 'knowledge',
    'understanding', 'work', 'role', 'team', 'company', 'candidate',
    'opportunity', 'applicants', 'employer', 'commitment', 'mindset',
    'responsibilities', 'requirements', 'qualifications', 'plus', 'bonus',
})


def _strip_leading_noise(text: str) -> str:
    """Drop leading articles and determiners: 'a growth mindset' -> 'growth mindset'."""
    words = text.split()
    while words and words[0].lower() in _LEADING_NOISE:
        words.pop(0)
    return ' '.join(words)


def is_usable_keyword(text: str) -> bool:
    """True when a string is specific enough to match a resume term against."""
    if not text:
        return False

    cleaned = _strip_leading_noise(text.strip())
    if not cleaned:
        return False

    # Must contain a letter — rejects "1-3", '("cv', bare punctuation.
    if not any(ch.isalpha() for ch in cleaned):
        return False

    if len(cleaned) > _MAX_KEYWORD_CHARS:
        return False

    words = cleaned.split()
    if not (1 <= len(words) <= _MAX_KEYWORD_WORDS):
        return False

    # Prose punctuation means this is a sentence fragment, not a term.
    if _PROSE_MARKERS.search(cleaned):
        return False

    # Every word being boilerplate ("years experience") carries no signal.
    if all(w.lower().strip('.,') in _BOILERPLATE for w in words):
        return False

    return True


def clean_keywords(items: Iterable[str]) -> List[str]:
    """Filter and tidy a keyword list, preserving order and dropping duplicates."""
    seen: Dict[str, str] = {}
    for raw in items:
        if not isinstance(raw, str):
            continue
        if not is_usable_keyword(raw):
            continue
        cleaned = _strip_leading_noise(raw.strip())
        key = cleaned.lower()
        if key not in seen:
            seen[key] = cleaned
    return list(seen.values())


def normalize_skill(skill: str) -> str:
    cleaned = skill.strip().lower()
    return SKILL_ALIASES.get(cleaned, cleaned)


def fuzzy_match_keywords(
    resume_keywords: List[str],
    jd_keywords: List[str],
    threshold: int = 80,
) -> Dict[str, List[str]]:
    resume_normalized = {normalize_skill(kw): kw for kw in resume_keywords}
    jd_normalized     = {normalize_skill(kw): kw for kw in jd_keywords}

    matched_jd_originals = []
    missing_jd_originals = []

    for jd_canon, jd_original in jd_normalized.items():
        # 1. Exact canonical match
        if jd_canon in resume_normalized:
            matched_jd_originals.append(jd_original)
            continue

        # 2. Fuzzy match against all resume canonical names
        best_score = 0
        for resume_canon in resume_normalized:
            score = fuzz.token_sort_ratio(jd_canon, resume_canon)
            best_score = max(best_score, score)

        if best_score >= threshold:
            matched_jd_originals.append(jd_original)
        else:
            missing_jd_originals.append(jd_original)

    return {
        'matched': sorted(matched_jd_originals),
        'missing': missing_jd_originals,
    }
