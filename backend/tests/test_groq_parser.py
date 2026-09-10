"""LLM response handling.

The Groq call itself is mocked — these test our parsing of what comes back,
which is where the original project's bugs lived.
"""

import json
from unittest.mock import patch

import pytest

from backend.services import groq_parser
from backend.services.groq_parser import (
    _try_parse_json,
    _validate_jd_result,
    _validate_resume_result,
    parse_job_description,
    parse_resume,
)

@pytest.fixture(autouse=True)
def _no_groq_client():
    """Every test here mocks `_call_groq`, so the real client is never used —
    but `parse_*` still constructs one. Stub it so tests need no API key."""
    with patch.object(groq_parser, '_get_client', return_value=object()):
        yield


VALID_RESUME_JSON = {
    'name': 'Alex Rivera',
    'email': 'alex@example.com',
    'skills': ['Python', 'FastAPI'],
    'experience': [{'job_title': 'Engineer', 'duration_months': '24'}],
    'projects': [{'title': 'Ledger'}],
}


class TestTryParseJson:
    def test_parses_bare_json(self):
        assert _try_parse_json('{"a": 1}') == {'a': 1}

    def test_strips_markdown_fences(self):
        assert _try_parse_json('```json\n{"a": 1}\n```') == {'a': 1}

    def test_strips_unlabelled_fences(self):
        assert _try_parse_json('```\n{"a": 1}\n```') == {'a': 1}

    def test_tolerates_surrounding_whitespace(self):
        assert _try_parse_json('\n\n  {"a": 1}  \n') == {'a': 1}

    def test_returns_none_for_prose(self):
        assert _try_parse_json("Sure! Here's the JSON you asked for.") is None

    def test_returns_none_for_truncated_json(self):
        assert _try_parse_json('{"a": 1') is None


class TestParseResume:
    """Regression guard for the inverted None check that made a *successful*
    parse fall through to the retry path and crash."""

    def test_valid_first_response_is_returned_without_a_retry(self):
        with patch.object(
            groq_parser, '_call_groq', return_value=json.dumps(VALID_RESUME_JSON)
        ) as call:
            result = parse_resume('resume text')

        assert call.call_count == 1, 'a valid response must not trigger a retry'
        assert result['name'] == 'Alex Rivera'
        assert result['skills'] == ['Python', 'FastAPI']

    def test_invalid_response_triggers_exactly_one_retry(self):
        with patch.object(
            groq_parser,
            '_call_groq',
            side_effect=['not json at all', json.dumps(VALID_RESUME_JSON)],
        ) as call:
            result = parse_resume('resume text')

        assert call.call_count == 2
        assert result['name'] == 'Alex Rivera'

    def test_two_bad_responses_raise(self):
        with patch.object(groq_parser, '_call_groq', side_effect=['nope', 'still nope']):
            with pytest.raises(ValueError, match='unparseable'):
                parse_resume('resume text')

    def test_result_is_always_fully_populated(self):
        """Downstream code indexes these keys directly, so they must exist."""
        with patch.object(groq_parser, '_call_groq', return_value='{}'):
            result = parse_resume('resume text')

        for key in (
            'name', 'email', 'phone', 'linkedin', 'github', 'professional_summary',
            'skills', 'experience', 'education', 'certifications', 'projects',
            'action_verbs', 'keywords',
        ):
            assert key in result


class TestParseJobDescription:
    def test_valid_response_is_returned_without_a_retry(self):
        payload = {'job_title': 'Backend Engineer', 'required_skills': ['Python']}
        with patch.object(groq_parser, '_call_groq', return_value=json.dumps(payload)) as call:
            result = parse_job_description('job posting')

        assert call.call_count == 1
        assert result['job_title'] == 'Backend Engineer'

    def test_result_is_always_fully_populated(self):
        with patch.object(groq_parser, '_call_groq', return_value='{}'):
            result = parse_job_description('job posting')

        for key in (
            'job_title', 'required_skills', 'preferred_skills',
            'experience_required', 'education_required',
            'key_responsibilities', 'keywords',
        ):
            assert key in result


class TestValidators:
    def test_null_fields_become_typed_defaults(self):
        result = _validate_resume_result({'skills': None, 'projects': None, 'email': None})
        assert result['skills'] == []
        assert result['projects'] == []
        assert result['email'] is None

    def test_wrongly_typed_list_fields_are_replaced(self):
        # The model sometimes returns a string where the schema asks for a list.
        result = _validate_resume_result({'skills': 'Python, FastAPI'})
        assert result['skills'] == []

    def test_duration_months_is_coerced_to_int(self):
        result = _validate_resume_result({'experience': [{'duration_months': '24'}]})
        assert result['experience'][0]['duration_months'] == 24

    def test_unparseable_duration_becomes_zero(self):
        result = _validate_resume_result({'experience': [{'duration_months': 'about two years'}]})
        assert result['experience'][0]['duration_months'] == 0

    def test_experience_entries_get_every_field(self):
        result = _validate_resume_result({'experience': [{'company': 'Acme'}]})
        entry = result['experience'][0]
        assert entry['job_title'] == ''
        assert entry['description'] == ''
        assert entry['duration_months'] == 0

    def test_project_entries_get_every_field(self):
        result = _validate_resume_result({'projects': [{'title': 'Ledger'}]})
        assert result['projects'][0]['technologies'] == []
        assert result['projects'][0]['description'] == ''

    def test_jd_null_lists_become_empty_lists(self):
        result = _validate_jd_result({'required_skills': None, 'keywords': None})
        assert result['required_skills'] == []
        assert result['keywords'] == []
