import os
import sys
from pathlib import Path

import pytest

# Make `import backend.…` work no matter where pytest is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Rate limits are production behaviour, not something the rest of the suite
# should have to budget around — a handful of analyze tests would otherwise
# exhaust the hourly allowance and fail the run. Must be set before
# backend.core.rate_limit is imported, since the Limiter reads it at import.
# test_rate_limit.py re-enables it deliberately.
os.environ.setdefault('RATE_LIMIT_ENABLED', 'false')


class FakeEmbedder:
    """Stand-in for SentenceTransformer.

    Returns a deterministic bag-of-characters vector, so cosine similarity is
    high for texts sharing letters and low otherwise. Enough to exercise the
    branching in validate_skills_with_projects without loading a real model.
    """

    def encode(self, text, convert_to_tensor=False):
        import numpy as np

        vector = np.zeros(26, dtype=float)
        for char in str(text).lower():
            index = ord(char) - 97
            if 0 <= index < 26:
                vector[index] += 1.0
        norm = np.linalg.norm(vector)
        return vector / norm if norm else vector


@pytest.fixture
def embedder():
    return FakeEmbedder()


@pytest.fixture
def parsed_resume():
    """A well-formed parsed resume — the shape groq_parser guarantees."""
    return {
        'name': 'Alex Rivera',
        'email': 'alex@example.com',
        'phone': '+1-555-0100',
        'linkedin': 'linkedin.com/in/alexrivera',
        'github': 'github.com/alexrivera',
        'professional_summary': (
            'Backend engineer with three years building payment systems at scale.'
        ),
        'skills': ['Python', 'FastAPI', 'PostgreSQL', 'Docker', 'Redis'],
        'experience': [
            {
                'job_title': 'Backend Engineer',
                'company': 'Acme Payments',
                'start_date': 'Jan 2022',
                'end_date': 'Present',
                'duration_months': 36,
                'description': (
                    'Developed FastAPI services in Python handling 40K requests/day.\n'
                    'Reduced p99 latency by 45% with Redis caching.\n'
                    'Migrated billing tables to PostgreSQL with zero downtime.'
                ),
            }
        ],
        'education': [
            {'degree': 'BSc Computer Science', 'institution': 'State University', 'year': '2021'}
        ],
        'certifications': [],
        'projects': [
            {
                'title': 'Ledger Service',
                'description': 'Double-entry ledger built with Python and PostgreSQL, containerised with Docker.',
                'technologies': ['Python', 'PostgreSQL', 'Docker'],
            }
        ],
        'action_verbs': ['Developed', 'Reduced', 'Migrated', 'Built', 'Deployed'],
        'keywords': [
            'python', 'fastapi', 'postgresql', 'docker', 'redis',
            'payments', 'rest api', 'caching', 'billing',
        ],
    }


@pytest.fixture(scope='session')
def nlp():
    """Real spaCy pipeline — the location detector relies on its NER, so a
    stub wouldn't test anything. Skips if no model is installed."""
    import spacy

    for model in ('en_core_web_md', 'en_core_web_sm'):
        try:
            return spacy.load(model)
        except OSError:
            continue
    pytest.skip('No spaCy model installed — run: python -m spacy download en_core_web_md')
