"""Request rate limiting.

The analyze endpoint is the expensive one: it spends Groq tokens and several
seconds of CPU on the embedding model. Without a limit, a public deployment
lets any caller drain the project's Groq quota.

Limits are per identity — the authenticated user id where there is one, falling
back to client IP. That matters behind a proxy, where every request otherwise
shares the load balancer's address.

Storage is in-process, which is correct for a single-container deployment and
resets on restart. Running more than one replica needs a shared backend; set
RATE_LIMIT_STORAGE_URI to a Redis URL and slowapi will use it.
"""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

# Generous enough that normal use never notices, tight enough that scripted
# abuse hits the wall quickly.
ANALYZE_LIMIT = os.getenv('RATE_LIMIT_ANALYZE', '10/hour')
REPORT_LIMIT = os.getenv('RATE_LIMIT_REPORTS', '30/hour')
DEFAULT_LIMIT = os.getenv('RATE_LIMIT_DEFAULT', '120/minute')

RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() != 'false'


def _client_id(request: Request) -> str:
    """Identify the caller for limiting purposes.

    Prefers the authenticated user so one user on a shared IP (an office, a
    university) can't exhaust everyone else's allowance. Falls back to the
    client address for unauthenticated requests.

    The token is read without verifying it — a forged token only ever changes
    which bucket the request is counted against, and the endpoint itself still
    rejects it. Verifying here would mean doing the JWKS work twice.
    """
    auth = request.headers.get('authorization', '')
    if auth.lower().startswith('bearer '):
        token = auth[7:].strip()
        if token:
            # The raw token is a stable per-session identifier; hashing keeps
            # it out of any limiter logging.
            return f'tok:{hash(token)}'

    forwarded = request.headers.get('x-forwarded-for', '')
    if forwarded:
        return f'ip:{forwarded.split(",")[0].strip()}'

    return f'ip:{get_remote_address(request)}'


limiter = Limiter(
    key_func=_client_id,
    default_limits=[DEFAULT_LIMIT] if RATE_LIMIT_ENABLED else [],
    storage_uri=os.getenv('RATE_LIMIT_STORAGE_URI', 'memory://'),
    enabled=RATE_LIMIT_ENABLED,
    headers_enabled=True,   # emit X-RateLimit-* so clients can back off
)
