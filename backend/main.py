import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.api.routes import router
from backend.core.rate_limit import limiter
from backend.core.config import (
    ALLOWED_ORIGINS,
    APP_DESCRIPTION,
    APP_TITLE,
    APP_VERSION,
    SENTENCE_TRANSFORMER_MODEL,
    SPACY_MODEL_PRIMARY,
    SPACY_MODEL_SECONDARY,
)

logger = logging.getLogger('ats_resume_scorer')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the NLP models once at startup — they take seconds and are reused
    across every request via app.state."""
    logger.info('Starting ATS Resume Analyzer API...')

    import spacy

    try:
        app.state.nlp = spacy.load(SPACY_MODEL_PRIMARY)
        logger.info(f'Loaded spaCy model {SPACY_MODEL_PRIMARY}')
    except OSError:
        logger.warning(f'{SPACY_MODEL_PRIMARY} not found — falling back to {SPACY_MODEL_SECONDARY}')
        app.state.nlp = spacy.load(SPACY_MODEL_SECONDARY)
        logger.info(f'Loaded spaCy model {SPACY_MODEL_SECONDARY} (fallback)')

    from sentence_transformers import SentenceTransformer

    app.state.embedder = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
    logger.info(f'Loaded sentence-transformer {SENTENCE_TRANSFORMER_MODEL}')

    logger.info('Models loaded — API ready.')
    yield
    logger.info('Shutting down.')


app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url='/docs',
    redoc_url='/redoc',
)

# Rate limiting. The middleware applies the default limit to every route;
# per-route decorators tighten it where a request is expensive.
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request, exc: RateLimitExceeded):
    """Answer with a readable message and Retry-After rather than slowapi's
    terse default, so the frontend can show something useful."""
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=429,
        content={
            'detail': (
                'Too many requests. This is a portfolio deployment with a '
                'shared API budget — please wait a little and try again.'
            )
        },
        headers={'Retry-After': '60'},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(router)


@app.get('/', include_in_schema=False)
async def root() -> dict:
    return {
        'name': APP_TITLE,
        'version': APP_VERSION,
        'docs': '/docs',
        'endpoints': {
            'POST   /api/v1/analyze-resume': 'Analyze a resume',
            'GET    /api/v1/health': 'Health check',
            'GET    /api/v1/history': "List the caller's analyses",
            'DELETE /api/v1/history/{id}': 'Delete one analysis',
            'GET    /api/v1/history/{id}/pdf': 'PDF for a saved analysis',
            'POST   /api/v1/reports/pdf': 'PDF for an analysis payload',
        },
    }
