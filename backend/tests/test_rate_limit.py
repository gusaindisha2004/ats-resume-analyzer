"""Rate limiting.

The rest of the suite runs with limits disabled (see conftest). These tests
turn the limiter back on deliberately, so the behaviour is still covered.
"""

import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request

from slowapi import Limiter

from backend.core.rate_limit import _client_id, limiter


def _make_request(headers: dict) -> Request:
    scope = {
        'type': 'http',
        'method': 'GET',
        'path': '/',
        'headers': [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        'client': ('203.0.113.7', 1234),
    }
    return Request(scope)


class TestClientIdentity:
    """Who a request is counted against."""

    def test_authenticated_callers_are_bucketed_by_token(self):
        one = _client_id(_make_request({'authorization': 'Bearer token-aaa'}))
        two = _client_id(_make_request({'authorization': 'Bearer token-bbb'}))
        assert one.startswith('tok:')
        assert one != two, 'different users must not share an allowance'

    def test_the_same_token_maps_to_the_same_bucket(self):
        headers = {'authorization': 'Bearer token-aaa'}
        assert _client_id(_make_request(headers)) == _client_id(_make_request(headers))

    def test_the_raw_token_is_not_used_as_the_key(self):
        """The key can end up in limiter storage and logs — don't put a
        credential there verbatim."""
        key = _client_id(_make_request({'authorization': 'Bearer secret-token-value'}))
        assert 'secret-token-value' not in key

    def test_anonymous_callers_fall_back_to_ip(self):
        key = _client_id(_make_request({}))
        assert key == 'ip:203.0.113.7'

    def test_proxy_header_is_preferred_over_socket_address(self):
        """Behind a load balancer every request shares one socket address, so
        the forwarded client address is what distinguishes callers."""
        key = _client_id(_make_request({'x-forwarded-for': '198.51.100.4, 10.0.0.1'}))
        assert key == 'ip:198.51.100.4'

    def test_an_empty_bearer_header_does_not_crash(self):
        assert _client_id(_make_request({'authorization': 'Bearer '})).startswith('ip:')


class TestLimitEnforcement:
    """A miniature app, so the real endpoints' quotas aren't spent here.

    Each test gets its own Limiter rather than the application one. Reusing the
    global limiter would re-register the same endpoint on every fixture run,
    stacking a fresh limit each time — by the fourth test a single request
    counts against four limits and 429s immediately. The key function is the
    real one, which is the part being tested.
    """

    @pytest.fixture
    def app(self):
        test_limiter = Limiter(
            key_func=_client_id,
            storage_uri='memory://',
            enabled=True,
            headers_enabled=True,
        )

        app = FastAPI()
        app.state.limiter = test_limiter
        app.add_middleware(SlowAPIMiddleware)

        @app.exception_handler(RateLimitExceeded)
        async def _handler(request, exc):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                content={'detail': 'Too many requests.'},
                headers={'Retry-After': '60'},
            )

        @app.get('/cheap')
        @test_limiter.limit('3/minute')
        async def cheap(request: Request, response: Response):
            return {'ok': True}

        return app

    def test_requests_under_the_limit_succeed(self, app):
        with TestClient(app) as client:
            for _ in range(3):
                assert client.get('/cheap').status_code == 200

    def test_exceeding_the_limit_returns_429(self, app):
        with TestClient(app) as client:
            for _ in range(3):
                client.get('/cheap')
            response = client.get('/cheap')

        assert response.status_code == 429
        assert 'Retry-After' in response.headers

    def test_the_429_body_explains_itself(self, app):
        with TestClient(app) as client:
            for _ in range(4):
                response = client.get('/cheap')
        assert 'Too many requests' in response.json()['detail']

    def test_separate_callers_have_separate_allowances(self, app):
        """One user hitting the wall must not lock everyone else out."""
        with TestClient(app) as client:
            for _ in range(4):
                client.get('/cheap', headers={'authorization': 'Bearer user-one'})

            blocked = client.get('/cheap', headers={'authorization': 'Bearer user-one'})
            other = client.get('/cheap', headers={'authorization': 'Bearer user-two'})

        assert blocked.status_code == 429
        assert other.status_code == 200


class TestWiring:
    """The real app must actually have the limiter attached."""

    def test_app_exposes_the_limiter(self):
        from backend.main import app

        assert getattr(app.state, 'limiter', None) is limiter

    def test_rate_limit_exceeded_has_a_handler(self):
        from backend.main import app

        assert RateLimitExceeded in app.exception_handlers

    def test_limits_are_configurable_from_the_environment(self):
        from backend.core import rate_limit

        assert rate_limit.ANALYZE_LIMIT
        assert rate_limit.REPORT_LIMIT
        assert rate_limit.DEFAULT_LIMIT
