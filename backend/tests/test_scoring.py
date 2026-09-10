"""Scoring components and aggregation.

These are the numbers users see, so the tests pin down the bounds and the
direction of each signal rather than exact magic values.
"""

import pytest

from backend.services.ats_scorer import (
    _calc_ats_compatibility_score,
    _calc_content_score,
    _calc_formatting_score,
    _calc_keywords_score,
    _tier_score,
    calculate_overall_score,
    detect_location_info,
    validate_skills_with_projects,
)
from backend.utils.file_utils import get_default_grammar_results, get_default_location_results

RESUME_TEXT = """
ALEX RIVERA
alex@example.com | +1-555-0100 | linkedin.com/in/alexrivera

SUMMARY
Backend engineer with three years building payment systems at scale.

EXPERIENCE
Backend Engineer - Acme Payments (Jan 2022 - Present)
- Developed FastAPI services in Python handling 40K requests/day
- Reduced p99 latency by 45% through Redis caching
- Migrated billing tables to PostgreSQL with zero downtime

PROJECTS
- Ledger Service: double-entry ledger in Python and PostgreSQL

EDUCATION
BSc Computer Science - State University, 2021

SKILLS
Python, FastAPI, PostgreSQL, Docker, Redis
"""


class TestTierScore:
    def test_returns_points_for_the_first_threshold_met(self):
        tiers = [(15, 5.0), (10, 4.0), (5, 3.0)]
        assert _tier_score(20, tiers) == 5.0
        assert _tier_score(15, tiers) == 5.0
        assert _tier_score(12, tiers) == 4.0
        assert _tier_score(5, tiers) == 3.0

    def test_returns_zero_below_every_threshold(self):
        assert _tier_score(1, [(15, 5.0), (10, 4.0)]) == 0.0


class TestFormattingScore:
    def test_complete_resume_scores_well(self, parsed_resume):
        score = _calc_formatting_score(parsed_resume, RESUME_TEXT)
        assert 12.0 <= score <= 20.0

    def test_empty_resume_scores_zero(self):
        empty = {'experience': [], 'education': [], 'skills': [], 'projects': [], 'professional_summary': ''}
        assert _calc_formatting_score(empty, '') == 0.0

    def test_never_exceeds_its_maximum(self, parsed_resume):
        # Even with an absurd number of bullets, formatting caps at 20.
        text = RESUME_TEXT + '\n'.join(['- did a thing'] * 200)
        assert _calc_formatting_score(parsed_resume, text) <= 20.0

    def test_missing_sections_score_lower_than_complete_ones(self, parsed_resume):
        stripped = {**parsed_resume, 'projects': [], 'education': []}
        assert _calc_formatting_score(stripped, RESUME_TEXT) < _calc_formatting_score(
            parsed_resume, RESUME_TEXT
        )


class TestKeywordsScore:
    def test_bounded_by_its_maximum(self, parsed_resume):
        score = _calc_keywords_score(
            parsed_resume['keywords'] * 10, parsed_resume['skills'] * 10
        )
        assert score <= 25.0

    def test_no_keywords_scores_zero(self):
        assert _calc_keywords_score([], []) == 0.0

    def test_matching_the_jd_beats_missing_it(self, parsed_resume):
        aligned = _calc_keywords_score(
            parsed_resume['keywords'], parsed_resume['skills'],
            jd_keywords=['Python', 'FastAPI', 'PostgreSQL', 'Redis'],
        )
        unrelated = _calc_keywords_score(
            parsed_resume['keywords'], parsed_resume['skills'],
            jd_keywords=['Salesforce', 'SAP', 'COBOL', 'Fortran'],
        )
        assert aligned > unrelated


class TestContentScore:
    def test_quantified_achievements_beat_vague_ones(self):
        grammar = get_default_grammar_results()
        verbs = ['Developed', 'Reduced', 'Migrated', 'Built', 'Led']

        quantified = _calc_content_score(
            'Reduced latency by 45%. Served 40K users. Saved $12000 annually.',
            verbs, grammar,
        )
        vague = _calc_content_score(
            'Responsible for the backend. Worked on performance. Helped the team.',
            verbs, grammar,
        )
        assert quantified > vague

    def test_bounded_by_its_maximum(self):
        assert _calc_content_score(
            'Improved throughput by 90% for 100000 users saving $50000',
            ['Built'] * 50, get_default_grammar_results(),
        ) <= 25.0


class TestAtsCompatibilityScore:
    def test_clean_resume_scores_near_the_top(self, parsed_resume):
        score = _calc_ats_compatibility_score(
            RESUME_TEXT, get_default_location_results(), parsed_resume
        )
        assert score >= 13.0

    def test_box_drawing_characters_are_penalised(self, parsed_resume):
        noisy = RESUME_TEXT + '╔' + '═' * 30 + '╗' + '║' * 20
        assert _calc_ats_compatibility_score(
            noisy, get_default_location_results(), parsed_resume
        ) < _calc_ats_compatibility_score(
            RESUME_TEXT, get_default_location_results(), parsed_resume
        )

    def test_privacy_penalty_reduces_the_score(self, parsed_resume):
        risky = {**get_default_location_results(), 'penalty_applied': 5.0}
        assert _calc_ats_compatibility_score(RESUME_TEXT, risky, parsed_resume) < (
            _calc_ats_compatibility_score(RESUME_TEXT, get_default_location_results(), parsed_resume)
        )

    def test_never_goes_negative(self, parsed_resume):
        brutal = {**get_default_location_results(), 'penalty_applied': 999.0}
        assert _calc_ats_compatibility_score(RESUME_TEXT, brutal, parsed_resume) == 0.0


class TestSkillValidation:
    def test_skills_named_in_projects_are_validated(self, embedder):
        result = validate_skills_with_projects(
            skills=['Python', 'PostgreSQL'],
            projects=[{'title': 'Ledger', 'description': 'Built in Python with PostgreSQL'}],
            experience_entries=[],
            embedder=embedder,
        )
        validated = {item['skill'] for item in result['validated_skills']}
        assert validated == {'Python', 'PostgreSQL'}
        assert result['validation_percentage'] == 1.0

    def test_skill_mentioned_nowhere_is_unvalidated(self, embedder):
        result = validate_skills_with_projects(
            skills=['Kubernetes'],
            projects=[{'title': 'Blog', 'description': 'A static site'}],
            experience_entries=[],
            # A high threshold keeps the fake embedder's fuzzy similarity from
            # accidentally validating an unrelated skill.
            embedder=embedder,
            threshold=0.99,
        )
        assert result['unvalidated_skills'] == ['Kubernetes']
        assert result['validation_percentage'] == 0.0

    def test_experience_alone_can_validate_a_skill(self, embedder):
        result = validate_skills_with_projects(
            skills=['Redis'],
            projects=[],
            experience_entries=[
                {'job_title': 'Engineer', 'company': 'Acme', 'description': 'Added Redis caching'}
            ],
            embedder=embedder,
        )
        assert result['validated_skills'][0]['projects'] == ['Experience Section']

    def test_no_skills_returns_a_zeroed_result(self, embedder):
        result = validate_skills_with_projects([], [], [], embedder)
        assert result['validation_percentage'] == 0.0
        assert result['validation_score'] == 0.0

    def test_validation_score_stays_within_its_component_max(self, embedder):
        result = validate_skills_with_projects(
            skills=['Python'],
            projects=[{'title': 'P', 'description': 'Python'}],
            experience_entries=[],
            embedder=embedder,
        )
        assert 0.0 <= result['validation_score'] <= 15.0


class TestLocationDetection:
    """Regression guard: this ran nowhere in the original project."""

    def test_street_address_and_zip_are_high_risk(self, nlp):
        result = detect_location_info('123 Maple Street, Springfield 62704', nlp)
        assert result['privacy_risk'] == 'high'
        assert result['penalty_applied'] > 0

    def test_clean_resume_has_no_penalty(self, nlp):
        result = detect_location_info('Backend engineer. Python, Redis, Docker.', nlp)
        assert result['penalty_applied'] == 0.0


class TestOverallScore:
    def _score(self, parsed_resume, embedder, jd_keywords=None):
        validation = validate_skills_with_projects(
            parsed_resume['skills'], parsed_resume['projects'],
            parsed_resume['experience'], embedder,
        )
        return calculate_overall_score(
            text=RESUME_TEXT,
            parsed_resume=parsed_resume,
            skills=parsed_resume['skills'],
            keywords=parsed_resume['keywords'],
            action_verbs=parsed_resume['action_verbs'],
            skill_validation_results=validation,
            grammar_results=get_default_grammar_results(),
            location_results=get_default_location_results(),
            jd_keywords=jd_keywords,
            experience_months=36,
        )

    def test_overall_score_is_a_percentage(self, parsed_resume, embedder):
        assert 0.0 <= self._score(parsed_resume, embedder)['overall_score'] <= 100.0

    def test_every_component_stays_within_its_own_maximum(self, parsed_resume, embedder):
        scores = self._score(parsed_resume, embedder)
        assert scores['formatting_score'] <= 20.0
        assert scores['keywords_score'] <= 25.0
        assert scores['content_score'] <= 25.0
        assert scores['skill_validation_score'] <= 15.0
        assert scores['ats_compatibility_score'] <= 15.0

    def test_a_strong_resume_outscores_an_empty_one(self, parsed_resume, embedder):
        empty = {
            'experience': [], 'education': [], 'skills': [],
            'projects': [], 'professional_summary': '', 'keywords': [], 'action_verbs': [],
        }
        strong = self._score(parsed_resume, embedder)['overall_score']
        weak = calculate_overall_score(
            text='', parsed_resume=empty, skills=[], keywords=[], action_verbs=[],
            skill_validation_results=validate_skills_with_projects([], [], [], embedder),
            grammar_results=get_default_grammar_results(),
            location_results=get_default_location_results(),
        )['overall_score']
        assert strong > weak

    def test_missing_most_jd_keywords_is_penalised(self, parsed_resume, embedder):
        aligned = self._score(parsed_resume, embedder, jd_keywords=['Python', 'FastAPI', 'Redis'])
        misaligned = self._score(
            parsed_resume, embedder,
            jd_keywords=['COBOL', 'Fortran', 'SAP', 'Salesforce', 'Mainframe'],
        )
        assert misaligned['overall_score'] < aligned['overall_score']
        assert 'missing_jd_keywords' in misaligned['penalties']

    def test_interpretation_accompanies_every_score(self, parsed_resume, embedder):
        assert self._score(parsed_resume, embedder)['overall_interpretation']

    @pytest.mark.parametrize('months', [0, 6, 120])
    def test_score_stays_in_range_across_experience_levels(self, parsed_resume, embedder, months):
        scores = calculate_overall_score(
            text=RESUME_TEXT, parsed_resume=parsed_resume,
            skills=parsed_resume['skills'], keywords=parsed_resume['keywords'],
            action_verbs=parsed_resume['action_verbs'],
            skill_validation_results=validate_skills_with_projects(
                parsed_resume['skills'], parsed_resume['projects'],
                parsed_resume['experience'], embedder,
            ),
            grammar_results=get_default_grammar_results(),
            location_results=get_default_location_results(),
            experience_months=months,
        )
        assert 0.0 <= scores['overall_score'] <= 100.0
