"""End-to-end analysis pipeline.

Only the Groq call is mocked. spaCy, the sentence-transformer, the scorer, the
feedback engine and the response model are all real — so this catches the kind
of key-mismatch break that unit tests miss.
"""

import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from backend.models.schemas import AnalysisResponse
from backend.services import groq_parser
from backend.services.resume_analyzer import analyze_full_resume

RESUME_TEXT = """
ALEX RIVERA
alex@example.com | +1-555-0100 | linkedin.com/in/alexrivera | github.com/alexrivera

SUMMARY
Backend engineer with three years building payment systems at scale.

EXPERIENCE
Backend Engineer - Acme Payments (Jan 2022 - Present)
- Developed FastAPI services in Python handling 40K requests/day
- Reduced p99 latency by 45% through Redis caching
- Migrated billing tables to PostgreSQL with zero downtime

PROJECTS
- Ledger Service: double-entry ledger in Python and PostgreSQL, containerised with Docker

EDUCATION
BSc Computer Science - State University, 2021

SKILLS
Python, FastAPI, PostgreSQL, Docker, Redis
"""

JOB_DESCRIPTION = """
Senior Backend Engineer

Required: Python, FastAPI, PostgreSQL, distributed systems, REST API design.
Preferred: Kubernetes, Terraform, Kafka.
"""

RESUME_JSON = {
    'name': 'Alex Rivera',
    'email': 'alex@example.com',
    'phone': '+1-555-0100',
    'linkedin': 'linkedin.com/in/alexrivera',
    'github': 'github.com/alexrivera',
    'professional_summary': 'Backend engineer with three years building payment systems at scale.',
    'skills': ['Python', 'FastAPI', 'PostgreSQL', 'Docker', 'Redis'],
    'experience': [
        {
            'job_title': 'Backend Engineer',
            'company': 'Acme Payments',
            'start_date': 'Jan 2022',
            'end_date': 'Present',
            'duration_months': 36,
            'description': (
                'Developed FastAPI services in Python handling 40K requests/day\n'
                'Reduced p99 latency by 45% through Redis caching\n'
                'Migrated billing tables to PostgreSQL with zero downtime'
            ),
        }
    ],
    'education': [{'degree': 'BSc Computer Science', 'institution': 'State University', 'year': '2021'}],
    'certifications': [],
    'projects': [
        {
            'title': 'Ledger Service',
            'description': 'Double-entry ledger in Python and PostgreSQL, containerised with Docker',
            'technologies': ['Python', 'PostgreSQL', 'Docker'],
        }
    ],
    'action_verbs': ['Developed', 'Reduced', 'Migrated'],
    'keywords': ['python', 'fastapi', 'postgresql', 'docker', 'redis', 'rest api', 'payments'],
}

JD_JSON = {
    'job_title': 'Senior Backend Engineer',
    'required_skills': ['Python', 'FastAPI', 'PostgreSQL', 'REST API design'],
    'preferred_skills': ['Kubernetes', 'Terraform', 'Kafka'],
    'experience_required': '5+ years',
    'education_required': "Bachelor's",
    'key_responsibilities': ['Design APIs'],
    'keywords': ['Python', 'FastAPI', 'PostgreSQL', 'Kubernetes', 'Kafka', 'distributed systems'],
}


@pytest.fixture(scope='module')
def embedder():
    """The real model — this suite is about integration, not isolation."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer('all-MiniLM-L6-v2')


def _fake_groq(system_prompt, user_prompt=None, *args, **kwargs):
    """Route to the right canned payload based on which prompt was sent."""
    prompt = user_prompt if user_prompt is not None else system_prompt
    return json.dumps(JD_JSON if 'job description' in str(prompt).lower() else RESUME_JSON)


@pytest.fixture
def run_pipeline(nlp, embedder):
    def _run(job_description=''):
        with patch.object(groq_parser, '_get_client', return_value=object()), patch.object(
            groq_parser, '_call_groq', side_effect=_fake_groq
        ):
            return analyze_full_resume(
                resume_text=RESUME_TEXT,
                nlp=nlp,
                embedder=embedder,
                job_description=job_description,
            )

    return _run


class TestWithoutJobDescription:
    def test_produces_a_valid_api_response(self, run_pipeline):
        """The analyzer's dict must satisfy the response model exactly — this is
        the contract the TypeScript client is generated from."""
        result = run_pipeline()
        response = AnalysisResponse(
            **result, filename='resume.pdf', analyzed_at=datetime.now(timezone.utc)
        )
        assert 0 <= response.ats_score <= 100
        assert response.interpretation
        assert response.jd_match is None

    def test_strengths_reach_the_response(self, run_pipeline):
        """Regression guard: the original computed strengths then dropped them
        on the floor when building the response."""
        response = AnalysisResponse(
            **run_pipeline(), filename='r.pdf', analyzed_at=datetime.now(timezone.utc)
        )
        assert len(response.strengths) > 0

    def test_component_scores_respect_their_maxima(self, run_pipeline):
        response = AnalysisResponse(
            **run_pipeline(), filename='r.pdf', analyzed_at=datetime.now(timezone.utc)
        )
        scores = response.component_scores
        for key, maximum in response.component_max.items():
            assert 0 <= getattr(scores, key) <= maximum, f'{key} out of range'

    def test_skills_are_validated_against_projects(self, run_pipeline):
        result = run_pipeline()
        validation = result['skill_validation']
        assert validation['total'] == len(RESUME_JSON['skills'])
        assert validation['validated_count'] > 0
        assert validation['validated_count'] + len(validation['unvalidated']) == validation['total']

    def test_grammar_report_reaches_the_response(self, run_pipeline):
        response = AnalysisResponse(
            **run_pipeline(), filename='r.pdf', analyzed_at=datetime.now(timezone.utc)
        )
        assert 0 <= response.grammar.score <= 100
        assert response.grammar.total_errors == (
            len(response.grammar.critical)
            + len(response.grammar.moderate)
            + len(response.grammar.minor)
        )

    def test_clean_resume_text_is_not_penalised_for_writing(self, run_pipeline):
        """The fixture resume is well written — it must not lose content points
        to phantom spelling errors on its technology names."""
        assert run_pipeline()['grammar']['critical'] == []

    def test_experience_months_are_summed(self, run_pipeline):
        assert run_pipeline()['experience_months'] == 36

    def test_issues_summary_matches_detailed_feedback(self, run_pipeline):
        result = run_pipeline()
        titles = [issue.issue_title for issue in result['detailed_feedback']]
        assert result['issues_summary'] == titles


class TestWithJobDescription:
    def test_jd_match_is_populated(self, run_pipeline):
        response = AnalysisResponse(
            **run_pipeline(JOB_DESCRIPTION),
            filename='r.pdf',
            analyzed_at=datetime.now(timezone.utc),
        )
        assert response.jd_match is not None
        assert 0 <= response.jd_match.match_percentage <= 100
        assert 0 <= response.jd_match.semantic_similarity <= 1

    def test_shared_skills_are_matched_and_absent_ones_are_missing(self, run_pipeline):
        jd = run_pipeline(JOB_DESCRIPTION)['jd_match']
        matched = {kw.lower() for kw in jd['matched_keywords']}
        missing = {kw.lower() for kw in jd['missing_keywords']}

        assert 'python' in matched
        assert 'kubernetes' in missing  # in the posting, nowhere in the resume
        assert not (matched & missing), 'a keyword cannot be both matched and missing'


class TestDegradedInput:
    """A nearly-empty resume must still produce a well-formed response rather
    than throwing — the frontend has no other error path for this."""

    @pytest.fixture
    def empty_result(self, nlp, embedder):
        blank = {key: ([] if isinstance(value, list) else '') for key, value in RESUME_JSON.items()}
        with patch.object(groq_parser, '_get_client', return_value=object()), patch.object(
            groq_parser, '_call_groq', return_value=json.dumps(blank)
        ):
            return analyze_full_resume(
                resume_text='John Doe', nlp=nlp, embedder=embedder, job_description=''
            )

    def test_still_builds_a_valid_response(self, empty_result):
        response = AnalysisResponse(
            **empty_result, filename='blank.pdf', analyzed_at=datetime.now(timezone.utc)
        )
        assert 0 <= response.ats_score <= 100

    def test_flags_the_missing_sections(self, empty_result):
        titles = ' '.join(empty_result['issues_summary']).lower()
        assert 'skills' in titles or 'experience' in titles

    def test_skill_validation_is_zeroed_not_absent(self, empty_result):
        assert empty_result['skill_validation']['total'] == 0
        assert empty_result['skill_validation']['validation_pct'] == 0.0
