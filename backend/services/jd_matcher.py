from typing import List, Dict
import numpy as np
import spacy
from sentence_transformers import SentenceTransformer

from typing import List, Dict
import numpy as np
import spacy
from sentence_transformers import SentenceTransformer

from backend.core.config import JD_KEYWORD_WEIGHT, JD_SEMANTIC_WEIGHT
from backend.utils.matching import clean_keywords, fuzzy_match_keywords, normalize_skill
from rapidfuzz import fuzz


def calculate_semantic_similarity(
    resume_text: str, jd_text: str, embedder: SentenceTransformer
) -> float:
    resume_emb = embedder.encode(resume_text[:5000], convert_to_tensor=False)
    jd_emb     = embedder.encode(jd_text[:5000], convert_to_tensor=False)

    similarity = np.dot(resume_emb, jd_emb) / (
        np.linalg.norm(resume_emb) * np.linalg.norm(jd_emb)
    )
    return float(np.clip(similarity, 0.0, 1.0))


def identify_matched_keywords(
    resume_keywords: List[str], jd_keywords: List[str]
) -> List[str]:
    result = fuzzy_match_keywords(resume_keywords, jd_keywords, threshold=80)
    return result['matched']


def identify_missing_keywords(
    resume_keywords: List[str], jd_keywords: List[str], top_n: int = 15
) -> List[str]:

    result = fuzzy_match_keywords(resume_keywords, jd_keywords, threshold=80)
    return result['missing'][:top_n]


def analyze_skills_gap(resume_skills: List[str], jd_skills: List[str]) -> List[str]:
    """Skills the posting asks for that the resume doesn't have.

    Sourced from the skills the LLM extracted from the posting, not from spaCy
    noun chunks over the raw text. Noun chunks are grammatical phrases, not
    skills — mining them produced "a growth mindset", "a related field",
    "an equal opportunity employer" and, memorably, '("cv'. The structured
    extraction is already the clean version of this.
    """
    resume_normalized = {normalize_skill(s) for s in resume_skills}

    gap = []
    for jd_skill in clean_keywords(jd_skills):
        jd_norm = normalize_skill(jd_skill)

        if jd_norm in resume_normalized:
            continue

        best_score = max(
            (fuzz.token_sort_ratio(jd_norm, rs) for rs in resume_normalized),
            default=0,
        )
        if best_score < 75:
            gap.append(jd_skill)

    return sorted(gap)[:20]


def calculate_match_percentage(
    resume_keywords: List[str],
    jd_keywords: List[str],
    semantic_similarity: float,
) -> float:
    if not jd_keywords:
        return 0.0
    matched = identify_matched_keywords(resume_keywords, jd_keywords)
    keyword_overlap = len(matched) / len(jd_keywords)
    match_pct = (
        keyword_overlap * JD_KEYWORD_WEIGHT
        + semantic_similarity * JD_SEMANTIC_WEIGHT
    ) * 100
    return float(np.clip(match_pct, 0.0, 100.0))


def compare_resume_with_jd(
    resume_text: str,
    resume_keywords: List[str],
    resume_skills: List[str],
    jd_text: str,
    jd_keywords: List[str],
    jd_skills: List[str],
    embedder: SentenceTransformer,
    nlp: spacy.Language = None,
) -> Dict:
    semantic_similarity = calculate_semantic_similarity(resume_text, jd_text, embedder)
    matched_keywords    = identify_matched_keywords(resume_keywords, jd_keywords)
    missing_keywords    = identify_missing_keywords(resume_keywords, jd_keywords)
    skills_gap          = analyze_skills_gap(resume_skills, jd_skills)
    match_percentage    = calculate_match_percentage(
        resume_keywords, jd_keywords, semantic_similarity
    )

    return {
        'match_percentage':    match_percentage,
        'semantic_similarity': semantic_similarity,
        'matched_keywords':    matched_keywords,
        'missing_keywords':    missing_keywords,
        'skills_gap':          skills_gap,
    }
