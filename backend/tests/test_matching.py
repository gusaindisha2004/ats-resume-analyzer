"""Keyword normalisation and fuzzy matching."""

import pytest

from backend.utils.matching import fuzzy_match_keywords, normalize_skill


@pytest.mark.parametrize(
    'raw, expected',
    [
        ('ReactJS', 'react'),
        ('react.js', 'react'),
        ('  NodeJS  ', 'node.js'),
        ('K8s', 'kubernetes'),
        ('ML', 'machine learning'),
        ('Postgres', 'postgresql'),
        ('Amazon Web Services', 'aws'),
        # Unknown skills pass through, lowercased and stripped.
        ('  Rust ', 'rust'),
    ],
)
def test_normalize_skill_resolves_aliases(raw, expected):
    assert normalize_skill(raw) == expected


def test_alias_makes_different_spellings_match():
    result = fuzzy_match_keywords(['ReactJS'], ['React.js'])
    assert result['matched'] == ['React.js']
    assert result['missing'] == []


def test_returns_the_job_descriptions_spelling_not_the_resumes():
    # The UI shows the JD's wording, so the user knows what the posting asked for.
    result = fuzzy_match_keywords(['postgres'], ['PostgreSQL'])
    assert result['matched'] == ['PostgreSQL']


def test_near_misses_match_above_threshold():
    result = fuzzy_match_keywords(['kubernetes'], ['Kubernetes'])
    assert result['matched'] == ['Kubernetes']


def test_unrelated_terms_are_missing():
    result = fuzzy_match_keywords(['python', 'django'], ['Golang', 'Kafka'])
    assert result['matched'] == []
    assert sorted(result['missing']) == ['Golang', 'Kafka']


def test_every_jd_keyword_lands_in_exactly_one_bucket():
    jd = ['Python', 'Kafka', 'Docker', 'Terraform']
    result = fuzzy_match_keywords(['python', 'docker'], jd)
    assert len(result['matched']) + len(result['missing']) == len(jd)


def test_empty_resume_means_everything_is_missing():
    result = fuzzy_match_keywords([], ['Python', 'AWS'])
    assert result['matched'] == []
    assert len(result['missing']) == 2


def test_empty_jd_produces_no_buckets():
    result = fuzzy_match_keywords(['Python'], [])
    assert result == {'matched': [], 'missing': []}
