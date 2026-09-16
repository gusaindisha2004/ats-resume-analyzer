"""Public API response models.

These are the single source of truth for the frontend's TypeScript types —
`web/src/lib/api/types.ts` is generated from the OpenAPI schema FastAPI derives
from this module. Renaming a field here is a breaking change for the client.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.core.config import SCORE_WEIGHTS

# Points each component contributes, straight from the single weight table.
# The frontend renders each component as `score / max`, and because the maxima
# are the weights, those five fractions add up to the overall score.
COMPONENT_MAX: Dict[str, float] = dict(SCORE_WEIGHTS)


class ComponentScores(BaseModel):
    """Per-component raw scores. Each is on its own scale — see COMPONENT_MAX."""

    formatting: float = Field(..., description='Section structure and bullets, out of 20')
    keywords: float = Field(..., description='Keyword and skill coverage, out of 25')
    content: float = Field(..., description='Action verbs and quantified impact, out of 25')
    skill_validation: float = Field(..., description='Skills backed by evidence, out of 15')
    ats_compatibility: float = Field(..., description='Parser-friendliness, out of 15')


class JDMatch(BaseModel):
    """Resume-versus-job-description comparison. Only present when a JD was supplied."""

    match_percentage: float = Field(..., description='Blended keyword + semantic match, 0-100')
    semantic_similarity: float = Field(..., description='Cosine similarity of embeddings, 0-1')
    matched_keywords: List[str] = []
    missing_keywords: List[str] = []
    skills_gap: List[str] = []


class ValidatedSkill(BaseModel):
    """A skill the analyzer found concrete evidence for."""

    skill: str
    projects: List[str] = Field(
        default=[],
        description="Project titles (or 'Experience Section') that demonstrate this skill",
    )
    similarity: Optional[float] = Field(
        default=None, description='Best match confidence, 0-1. 1.0 means a literal text match.'
    )


class SkillValidation(BaseModel):
    """How many claimed skills are actually demonstrated elsewhere in the resume."""

    validated: List[ValidatedSkill] = []
    unvalidated: List[str] = []
    total: int = 0
    validated_count: int = 0
    validation_pct: float = 0.0


class WritingIssue(BaseModel):
    """One spelling or style finding."""

    error_text: str = Field(..., description='The offending text as it appears')
    message: str = Field(..., description='What is wrong, in plain English')
    suggestions: List[str] = []
    context: str = Field('', description='Surrounding line, for locating it')


class GrammarReport(BaseModel):
    """Spelling and resume-writing-style findings, split by severity.

    `critical` is misspellings; `moderate` is style that costs a screen
    (first-person pronouns, duty-style bullet openers); `minor` is polish.
    """

    total_errors: int = 0
    score: float = Field(100.0, description='Writing quality, 0-100')
    critical: List[WritingIssue] = []
    moderate: List[WritingIssue] = []
    minor: List[WritingIssue] = []


class ScoreAdjustment(BaseModel):
    """A bonus or penalty applied to the summed component total.

    Without these, the five component scores wouldn't add up to the overall
    score and the difference would be unexplained.
    """

    label: str
    points: float = Field(..., description='Signed; negative is a penalty')
    reason: str


class IssueDetail(BaseModel):
    """One specific, actionable problem found in the resume."""

    issue_title: str
    severity_level: str = Field(..., description='High | Moderate | Low')
    ats_impact: str = Field(..., description='High | Medium | Low')
    explanation: str
    where_it_appears: str
    how_to_fix: str
    action_items: List[str] = []
    example_improvement: str


class AnalysisResponse(BaseModel):
    """The complete result of one resume analysis."""

    ats_score: float = Field(..., description='Overall score, 0-100')
    interpretation: str = Field('', description='One-line plain-English reading of the score')
    component_scores: ComponentScores
    component_max: Dict[str, float] = Field(
        default_factory=lambda: dict(COMPONENT_MAX),
        description='Points each component contributes; these sum to 100',
    )
    base_score: float = Field(
        0.0, description='Sum of the component scores, before adjustments'
    )
    adjustments: List[ScoreAdjustment] = Field(
        [], description='Bonuses and penalties applied to the component total'
    )

    strengths: List[str] = []
    issues_summary: List[str] = Field([], description='Issue titles, for an at-a-glance list')
    detailed_feedback: List[IssueDetail] = []

    skill_validation: SkillValidation
    grammar: GrammarReport = Field(default_factory=GrammarReport)
    jd_match: Optional[JDMatch] = None

    skills: List[str] = Field([], description='Skills extracted from the resume')
    experience_months: int = 0

    filename: str = ''
    analyzed_at: datetime


class HistoryEntry(BaseModel):
    """One saved analysis, as listed on the history page."""

    id: str
    filename: str
    ats_score: float
    jd_match_percentage: Optional[float] = None
    created_at: datetime
    analysis: Optional[Dict[str, Any]] = Field(
        default=None, description='Full stored AnalysisResponse payload'
    )
