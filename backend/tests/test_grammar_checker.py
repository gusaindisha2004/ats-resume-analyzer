"""Spelling and resume-style checks.

The bar here is asymmetric: a missed typo is a small loss, but a false positive
on a technology name teaches the user to ignore the whole section. Most of
these tests are therefore about what must *not* be flagged.
"""

import pytest

from backend.services.grammar_checker import (
    _americanised,
    _is_checkable,
    check_grammar,
)

CLEAN_RESUME = """ALEX RIVERA
alex@example.com | linkedin.com/in/alexrivera | github.com/alexrivera

SUMMARY
Backend engineer with three years building payment systems at scale.

EXPERIENCE
Backend Engineer - Acme Payments (Jan 2022 - Present)
- Developed FastAPI services in Python handling 40K requests/day
- Reduced p99 latency by 45% through Redis caching
- Migrated billing tables to PostgreSQL with zero downtime
- Deployed microservices on Kubernetes using Terraform and Jenkins

SKILLS
Python, FastAPI, PostgreSQL, Docker, Redis, Kubernetes, TypeScript, GraphQL
"""


class TestIsCheckable:
    """The filter that decides whether a token is ordinary prose."""

    @pytest.mark.parametrize(
        'token', ['FastAPI', 'PostgreSQL', 'JavaScript', 'GraphQL', 'TypeScript']
    )
    def test_camelcase_product_names_are_skipped(self, token):
        assert not _is_checkable(token)

    @pytest.mark.parametrize('token', ['AWS', 'SQL', 'REST', 'CI'])
    def test_acronyms_are_skipped(self, token):
        assert not _is_checkable(token)

    @pytest.mark.parametrize('token', ['p99', 'x86', 'S3'])
    def test_tokens_with_digits_are_skipped(self, token):
        assert not _is_checkable(token)

    @pytest.mark.parametrize('token', ['kubernetes', 'postgres', 'microservices'])
    def test_lowercase_tech_vocabulary_is_skipped(self, token):
        assert not _is_checkable(token)

    def test_short_tokens_are_skipped(self):
        assert not _is_checkable('api')
        assert not _is_checkable('a')

    @pytest.mark.parametrize('token', ['developement', 'recieved', 'Managment'])
    def test_ordinary_words_are_checked(self, token):
        assert _is_checkable(token)


class TestBritishSpellings:
    @pytest.mark.parametrize(
        'british, american',
        [
            ('containerised', 'containerized'),
            ('optimised', 'optimized'),
            ('organisation', 'organization'),
            ('analyse', 'analyze'),
            ('behaviour', 'behavior'),
            ('catalogue', 'catalog'),
            ('modelling', 'modeling'),
        ],
    )
    def test_variant_is_generated(self, british, american):
        assert american in list(_americanised(british))


class TestNoFalsePositives:
    """A well-written resume must come back completely clean."""

    @pytest.fixture
    def clean(self, nlp):
        return check_grammar(
            CLEAN_RESUME, nlp, known_skills=['Python', 'FastAPI', 'PostgreSQL']
        )

    def test_clean_resume_has_no_findings(self, clean):
        assert clean['total_errors'] == 0, (
            f"false positives: {[e['error_text'] for e in clean['critical_errors']]}"
        )

    def test_clean_resume_takes_no_penalty(self, clean):
        assert clean['penalty_applied'] == 0.0
        assert clean['grammar_score'] == 100.0

    def test_urls_and_handles_are_not_spell_checked(self, nlp):
        result = check_grammar(
            'Portfolio: linkedin.com/in/janedoe and github.com/janedoe-dev', nlp
        )
        flagged = {e['error_text'].lower() for e in result['critical_errors']}
        assert 'janedoe' not in flagged
        assert 'linkedin' not in flagged

    def test_british_spellings_are_not_flagged(self, nlp):
        result = check_grammar(
            'Optimised and containerised the analytics pipeline.', nlp
        )
        assert result['critical_errors'] == []

    def test_candidate_skills_are_never_flagged(self, nlp):
        # An obscure tool the dictionary can't know, declared as a skill.
        result = check_grammar(
            'Built dashboards in Zylonix.', nlp, known_skills=['Zylonix']
        )
        assert result['critical_errors'] == []


class TestSpellingDetection:
    @pytest.fixture
    def misspelled(self, nlp):
        return check_grammar(
            'Responsibilities included backend developement and improving '
            'performace of the sytem.',
            nlp,
        )

    def test_typos_are_caught(self, misspelled):
        flagged = {e['error_text'].lower() for e in misspelled['critical_errors']}
        assert {'developement', 'performace', 'sytem'} <= flagged

    def test_corrections_are_suggested(self, misspelled):
        by_word = {
            e['error_text'].lower(): e['suggestions']
            for e in misspelled['critical_errors']
        }
        assert 'development' in by_word['developement']
        assert 'performance' in by_word['performace']


class TestStyleRules:
    def test_first_person_pronouns_are_flagged(self, nlp):
        result = check_grammar('I built the payment service myself.', nlp)
        assert any('first-person' in e['message'] for e in result['moderate_errors'])

    def test_weak_bullet_openers_are_flagged(self, nlp):
        result = check_grammar(
            '- Responsible for the backend\n- Assisted with deployments', nlp
        )
        messages = ' '.join(e['message'] for e in result['moderate_errors'])
        assert 'duty' in messages

    def test_strong_bullets_are_not_flagged_as_weak(self, nlp):
        result = check_grammar(
            '- Developed a REST API\n- Reduced latency by 40%', nlp
        )
        assert not any('duty' in e['message'] for e in result['moderate_errors'])

    def test_repeated_words_are_caught(self, nlp):
        result = check_grammar('Managed the the deployment pipeline.', nlp)
        assert any(
            'Repeated word' in e['message'] for e in result['moderate_errors']
        )

    def test_space_before_punctuation_is_minor(self, nlp):
        result = check_grammar('Shipped features , on schedule.', nlp)
        assert any("Space before" in e['message'] for e in result['minor_errors'])

    def test_lowercase_bullet_starts_are_minor(self, nlp):
        result = check_grammar('- developed an API\n- Built a service', nlp)
        assert any('lowercase' in e['message'] for e in result['minor_errors'])


class TestScoringContract:
    """The scorer consumes this dict — its shape and bounds must hold."""

    def test_returns_every_key_the_scorer_reads(self, nlp):
        result = check_grammar('Some resume text here.', nlp)
        for key in (
            'total_errors', 'critical_errors', 'moderate_errors', 'minor_errors',
            'grammar_score', 'penalty_applied', 'error_free_percentage',
        ):
            assert key in result

    def test_empty_text_returns_neutral_defaults(self, nlp):
        result = check_grammar('', nlp)
        assert result['total_errors'] == 0
        assert result['penalty_applied'] == 0

    def test_penalty_is_capped(self, nlp):
        # Enough garbage to blow past the cap several times over.
        result = check_grammar(' '.join(['developement'] * 200), nlp)
        assert result['penalty_applied'] <= 20.0

    def test_score_stays_in_range(self, nlp):
        result = check_grammar(' '.join(['sytem performace'] * 50), nlp)
        assert 0.0 <= result['grammar_score'] <= 100.0

    def test_total_matches_the_sum_of_buckets(self, nlp):
        result = check_grammar(
            'I was responsible for the the sytem developement , daily.', nlp
        )
        assert result['total_errors'] == (
            len(result['critical_errors'])
            + len(result['moderate_errors'])
            + len(result['minor_errors'])
        )

    def test_works_without_a_spacy_pipeline(self):
        """nlp is optional — the entity filter just degrades."""
        result = check_grammar('Developed a payment service.', nlp=None)
        assert 'total_errors' in result

    def test_messy_resume_scores_worse_than_clean(self, nlp):
        clean = check_grammar(CLEAN_RESUME, nlp, known_skills=['Python'])
        messy = check_grammar(
            'EXPERINCE\n- I was responsible for the the backend developement\n'
            '- worked on improving performace of the sytem ,',
            nlp,
        )
        assert messy['grammar_score'] < clean['grammar_score']
        assert messy['penalty_applied'] > clean['penalty_applied']
