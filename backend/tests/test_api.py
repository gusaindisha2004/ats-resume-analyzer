"""HTTP-level tests for the API.

These drive the real FastAPI app through TestClient: auth dependency, file
upload, status codes and response bodies. Only the network edges are mocked —
Groq and Supabase.
"""

import io
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.api.auth import get_current_user
from backend.main import app
from backend.services import groq_parser
from backend.tests.test_pipeline import _fake_groq

USER_ID = '11111111-2222-3333-4444-555555555555'


def _docx_bytes(paragraphs) -> bytes:
    from docx import Document

    document = Document()
    for line in paragraphs:
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


RESUME_DOCX = _docx_bytes([
    'ALEX RIVERA',
    'alex@example.com | linkedin.com/in/alexrivera',
    'EXPERIENCE',
    'Developed FastAPI services in Python handling 40K requests/day',
    'Reduced p99 latency by 45% through Redis caching',
    'SKILLS',
    'Python, FastAPI, PostgreSQL, Docker, Redis',
])


@pytest.fixture(scope='module')
def client(nlp):
    """App with models attached directly, bypassing the lifespan loader."""
    from sentence_transformers import SentenceTransformer

    app.state.nlp = nlp
    app.state.embedder = SentenceTransformer('all-MiniLM-L6-v2')
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth(client):
    """Treat the caller as signed in, without minting a real Supabase JWT."""
    app.dependency_overrides[get_current_user] = lambda: USER_ID
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def no_db():
    """Supabase isn't configured in tests; history calls must degrade quietly."""
    with patch('backend.database.supabase_db._headers', return_value=None):
        yield


class TestHealth:
    def test_health_reports_loaded_models(self, client):
        response = client.get('/api/v1/health')
        assert response.status_code == 200
        body = response.json()
        assert body['status'] == 'healthy'
        assert body['nlp_loaded'] is True
        assert body['embedder_loaded'] is True

    def test_root_lists_endpoints(self, client):
        assert client.get('/').status_code == 200

    def test_openapi_schema_is_served(self, client):
        assert client.get('/openapi.json').status_code == 200


class TestAuthGate:
    """Every data endpoint must reject an unauthenticated caller."""

    @pytest.mark.parametrize(
        'method, path',
        [
            ('post', '/api/v1/analyze-resume'),
            ('get', '/api/v1/history'),
            ('delete', '/api/v1/history/abc'),
            ('post', '/api/v1/reports/pdf'),
            ('get', '/api/v1/history/abc/pdf'),
        ],
    )
    def test_requires_a_bearer_token(self, client, method, path):
        assert getattr(client, method)(path).status_code == 401

    def test_rejects_a_garbage_token_when_auth_is_configured(self, client):
        # With a secret present the token is actually verified, so a malformed
        # one is the caller's fault: 401.
        with patch('backend.api.auth.SUPABASE_JWT_SECRET', 'test-secret'):
            response = client.get(
                '/api/v1/history', headers={'Authorization': 'Bearer not-a-jwt'}
            )
        assert response.status_code == 401
        assert 'Invalid token' in response.json()['detail']

    def test_expired_token_is_rejected(self, client):
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone

        secret = 'test-secret'
        expired = pyjwt.encode(
            {
                'sub': USER_ID,
                'aud': 'authenticated',
                'exp': datetime.now(timezone.utc) - timedelta(hours=1),
            },
            secret,
            algorithm='HS256',
        )
        with patch('backend.api.auth.SUPABASE_JWT_SECRET', secret):
            response = client.get(
                '/api/v1/history', headers={'Authorization': f'Bearer {expired}'}
            )
        assert response.status_code == 401
        assert 'expired' in response.json()['detail'].lower()

    def test_valid_token_is_accepted(self, client, no_db):
        """The happy path through real JWT verification — not the override."""
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone

        secret = 'test-secret'
        token = pyjwt.encode(
            {
                'sub': USER_ID,
                'aud': 'authenticated',
                'exp': datetime.now(timezone.utc) + timedelta(hours=1),
            },
            secret,
            algorithm='HS256',
        )
        with patch('backend.api.auth.SUPABASE_JWT_SECRET', secret):
            response = client.get(
                '/api/v1/history', headers={'Authorization': f'Bearer {token}'}
            )
        assert response.status_code == 200

    def test_unconfigured_server_reports_a_server_error_not_a_client_one(self, client):
        # No SUPABASE_URL and no secret: the caller did nothing wrong, so this
        # is a 500, not a 401.
        with patch('backend.api.auth.SUPABASE_URL', ''), patch(
            'backend.api.auth.SUPABASE_JWT_SECRET', ''
        ):
            response = client.get(
                '/api/v1/history', headers={'Authorization': 'Bearer whatever'}
            )
        assert response.status_code == 500
        assert 'not configured' in response.json()['detail'].lower()


class TestAnalyzeEndpoint:
    def _post(self, client, data=RESUME_DOCX, filename='resume.docx', jd=''):
        with patch.object(groq_parser, '_get_client', return_value=object()), patch.object(
            groq_parser, '_call_groq', side_effect=_fake_groq
        ):
            return client.post(
                '/api/v1/analyze-resume',
                files={
                    'resume': (
                        filename,
                        data,
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    )
                },
                data={'job_description': jd},
            )

    def test_returns_a_complete_analysis(self, client, auth, no_db):
        response = self._post(client)
        assert response.status_code == 200, response.text

        body = response.json()
        assert 0 <= body['ats_score'] <= 100
        assert body['filename'] == 'resume.docx'
        assert body['interpretation']
        assert body['jd_match'] is None
        # Every top-level key the frontend reads must be present.
        for key in (
            'component_scores', 'component_max', 'strengths', 'issues_summary',
            'detailed_feedback', 'skill_validation', 'grammar', 'skills',
            'experience_months', 'analyzed_at',
        ):
            assert key in body, f'missing {key}'

    def test_job_description_produces_a_match_block(self, client, auth, no_db):
        response = self._post(client, jd='Required: Python, FastAPI, Kubernetes, Kafka.')
        assert response.status_code == 200
        jd_match = response.json()['jd_match']
        assert jd_match is not None
        assert 0 <= jd_match['match_percentage'] <= 100

    def test_missing_file_is_a_validation_error(self, client, auth, no_db):
        assert client.post('/api/v1/analyze-resume', data={}).status_code == 422

    def test_unsupported_file_type_is_rejected_with_a_readable_message(
        self, client, auth, no_db
    ):
        response = self._post(client, data=b'just plain text', filename='resume.txt')
        assert response.status_code == 422
        assert 'pdf' in response.json()['detail'].lower()

    def test_empty_file_is_rejected(self, client, auth, no_db):
        response = self._post(client, data=b'', filename='empty.docx')
        assert response.status_code == 422
        assert 'empty' in response.json()['detail'].lower()

    def test_renamed_executable_is_rejected(self, client, auth, no_db):
        """Content decides the type, not the extension."""
        response = self._post(
            client, data=b'MZ\x90\x00 this is a PE binary', filename='resume.docx'
        )
        assert response.status_code == 422

    def test_oversized_file_is_rejected(self, client, auth, no_db):
        from backend.core.config import MAX_FILE_SIZE_BYTES

        oversized = b'%PDF-' + b'0' * MAX_FILE_SIZE_BYTES
        response = self._post(client, data=oversized, filename='big.pdf')
        assert response.status_code == 422
        assert 'MB' in response.json()['detail']

    def test_history_failure_does_not_fail_the_analysis(self, client, auth):
        """Saving is best-effort — a database outage must not lose the result."""
        with patch(
            'backend.database.supabase_db.save_analysis',
            side_effect=RuntimeError('supabase down'),
        ):
            assert self._post(client).status_code == 200

    def test_llm_failure_surfaces_as_a_server_error(self, client, auth, no_db):
        with patch.object(groq_parser, '_get_client', return_value=object()), patch.object(
            groq_parser, '_call_groq', side_effect=RuntimeError('groq unreachable')
        ):
            response = client.post(
                '/api/v1/analyze-resume',
                files={'resume': ('resume.docx', RESUME_DOCX, 'application/octet-stream')},
                data={'job_description': ''},
            )
        assert response.status_code == 500
        assert 'Analysis failed' in response.json()['detail']


class TestHistoryEndpoints:
    def test_history_is_empty_when_the_database_is_unconfigured(self, client, auth, no_db):
        response = client.get('/api/v1/history')
        assert response.status_code == 200
        assert response.json() == []

    def test_history_returns_saved_entries(self, client, auth):
        from backend.models.schemas import HistoryEntry

        entry = HistoryEntry(
            id='abc', filename='resume.docx', ats_score=71.0,
            jd_match_percentage=58.0, created_at='2026-09-11T09:00:00Z', analysis={},
        )
        with patch(
            'backend.database.supabase_db.get_user_history', return_value=[entry]
        ):
            response = client.get('/api/v1/history')

        assert response.status_code == 200
        assert response.json()[0]['filename'] == 'resume.docx'

    def test_deleting_a_missing_entry_is_404(self, client, auth):
        with patch('backend.database.supabase_db.delete_analysis', return_value=False):
            response = client.delete('/api/v1/history/does-not-exist')
        assert response.status_code == 404

    def test_deleting_an_owned_entry_succeeds(self, client, auth):
        with patch('backend.database.supabase_db.delete_analysis', return_value=True):
            response = client.delete('/api/v1/history/abc')
        assert response.status_code == 200
        assert response.json()['status'] == 'deleted'

    def test_pdf_for_a_missing_analysis_is_404(self, client, auth):
        with patch('backend.database.supabase_db.get_analysis', return_value=None):
            response = client.get('/api/v1/history/nope/pdf')
        assert response.status_code == 404


class TestPdfEndpoint:
    @pytest.fixture
    def payload(self, client, auth, no_db):
        with patch.object(groq_parser, '_get_client', return_value=object()), patch.object(
            groq_parser, '_call_groq', side_effect=_fake_groq
        ):
            response = client.post(
                '/api/v1/analyze-resume',
                files={'resume': ('resume.docx', RESUME_DOCX, 'application/octet-stream')},
                data={'job_description': ''},
            )
        return response.json()

    def test_returns_a_pdf_or_a_clear_503(self, client, auth, payload):
        """WeasyPrint needs native libraries. Either it renders, or it explains
        itself — an opaque 500 is the one unacceptable outcome."""
        response = client.post('/api/v1/reports/pdf', json=payload)
        assert response.status_code in (200, 503), response.text

        if response.status_code == 200:
            assert response.headers['content-type'] == 'application/pdf'
            assert response.content.startswith(b'%PDF')
        else:
            assert 'WeasyPrint' in response.json()['detail']

    def test_malformed_payload_is_rejected(self, client, auth):
        response = client.post('/api/v1/reports/pdf', json={'nonsense': True})
        assert response.status_code == 422


class TestStoredAnalysisCompatibility:
    """History rows are JSONB written by older versions of the app. They must
    survive a schema addition rather than reaching the UI half-formed."""

    OLD_ROW = {
        'id': 'abc',
        'filename': 'old.pdf',
        'ats_score': 70,
        'created_at': '2026-09-11T09:00:00Z',
        'analysis': {
            'ats_score': 70,
            'interpretation': 'Good',
            'component_scores': {
                'formatting': 16, 'keywords': 19, 'content': 18,
                'skill_validation': 9, 'ats_compatibility': 14,
            },
            'skill_validation': {
                'validated': [], 'unvalidated': [], 'total': 0,
                'validated_count': 0, 'validation_pct': 0,
            },
            'detailed_feedback': [], 'strengths': [], 'issues_summary': [],
            'skills': [], 'experience_months': 0, 'filename': 'old.pdf',
            'analyzed_at': '2026-09-11T09:00:00Z',
        },
    }

    def test_row_saved_before_grammar_existed_gains_the_default(self):
        from backend.database.supabase_db import _to_history_entry

        entry = _to_history_entry(self.OLD_ROW)
        assert 'grammar' in entry.analysis
        assert entry.analysis['grammar']['score'] == 100.0
        assert entry.analysis['grammar']['critical'] == []

    def test_existing_values_are_preserved(self):
        from backend.database.supabase_db import _to_history_entry

        entry = _to_history_entry(self.OLD_ROW)
        assert entry.analysis['ats_score'] == 70
        assert entry.analysis['component_scores']['keywords'] == 19

    def test_malformed_row_is_returned_rather_than_dropped(self):
        from backend.database.supabase_db import _to_history_entry

        entry = _to_history_entry({
            'id': 'x', 'filename': 'f', 'ats_score': 0,
            'created_at': '2026-09-11T09:00:00Z',
            'analysis': {'totally': 'malformed'},
        })
        assert entry.analysis == {'totally': 'malformed'}

    def test_empty_analysis_is_handled(self):
        from backend.database.supabase_db import _to_history_entry

        entry = _to_history_entry({
            'id': 'x', 'filename': 'f', 'ats_score': 0,
            'created_at': '2026-09-11T09:00:00Z', 'analysis': None,
        })
        assert entry.analysis == {}
