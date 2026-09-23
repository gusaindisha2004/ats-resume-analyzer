import os
from pathlib import Path

# Load .env from the project root (two levels up from this file) explicitly —
# load_dotenv() with no args relies on caller-frame inspection that can fail
# silently under uvicorn reload, leaving env vars unset.
try:
    from dotenv import load_dotenv
    _ENV_PATH = Path(__file__).resolve().parents[2] / '.env'
    load_dotenv(_ENV_PATH)
except ImportError:
    pass

#api metadata
APP_TITLE='ATS RESUME ANALYZER API'
APP_VERSION='1.0.0'
APP_DESCRIPTION='analyse resumes against job description using nlp + ml'

# Comma-separated list in the env var; sensible localhost defaults for dev.
# Origins must NOT have a trailing slash — CORS origin matching is exact.
ALLOWED_ORIGINS = [
    o.strip().rstrip('/')
    for o in os.getenv(
        'ALLOWED_ORIGINS',
        'http://localhost:3000,http://127.0.0.1:3000',
    ).split(',')
    if o.strip()
]

#file 
MAX_FILE_SIZE_MB=5
MAX_FILE_SIZE_BYTES=MAX_FILE_SIZE_MB*1024*1024

# Accepted document types. Detection is by file signature, not extension or
# MIME string — see backend/services/resume_parser.detect_file_type.
SUPPORTED_EXTENSIONS = {'.pdf', '.docx'}

SPACY_MODEL_PRIMARY="en_core_web_md" #better accuracy
SPACY_MODEL_SECONDARY = 'en_core_web_sm'
SENTENCE_TRANSFORMER_MODEL = os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")

# ── Scoring ─────────────────────────────────────────────────────────────────
# Points each component contributes to the final score out of 100. These ARE
# the weights — a component's score is computed directly on this scale and the
# five are summed, so the breakdown the user sees adds up to the total they
# were given. There is deliberately no second re-weighting layer.
#
# The ordering is a judgement call, reasoned as follows:
#
#   keywords (25)          An ATS screen is fundamentally keyword matching.
#                          Failing it means no human ever sees the resume.
#   content (25)           What a recruiter actually reads once past the
#                          filter: action verbs and quantified outcomes.
#   formatting (20)        A resume the parser mangles loses everything else,
#                          but modern parsers are tolerant enough that this
#                          ranks below the two above.
#   skill_validation (15)  Whether claimed skills are evidenced. A credibility
#                          signal a recruiter checks, not something an ATS
#                          scores — hence lower.
#   ats_compatibility (15) Specific parser hazards (tables, glyphs, addresses).
#                          Narrow, so weighted like the above.
#
# These are NOT fitted to outcome data. No public dataset of "resumes that
# passed an ATS" exists to calibrate against, so treat the score as a
# consistent rubric for comparing drafts of one resume rather than a
# prediction about any particular ATS. Changing a weight here changes the
# score everywhere, and the tests assert the total stays 100.
SCORE_WEIGHTS = {
    'keywords': 25.0,
    'content': 25.0,
    'formatting': 20.0,
    'skill_validation': 15.0,
    'ats_compatibility': 15.0,
}

# Blend used when comparing a resume against a job description: exact keyword
# overlap dominates because that is what an ATS matches on, with embedding
# similarity as a softer signal for wording the keyword pass would miss.
JD_KEYWORD_WEIGHT = 0.6
JD_SEMANTIC_WEIGHT = 0.4

# Adjustments applied to the summed total. Kept small on purpose: they nudge,
# they don't decide. Grammar and location penalties are NOT here — those are
# already subtracted inside the content and ats_compatibility components, and
# applying them again would double-count.
BONUS_SKILL_VALIDATION_EXCELLENT = 2.0   # >= 90% of skills evidenced
BONUS_SKILL_VALIDATION_GOOD = 1.0        # >= 80%
BONUS_CLEAN_WRITING = 1.0                # no spelling or style findings

# Missing a large share of a job description's keywords is the single clearest
# signal a resume will be filtered out, so it is the one large deduction.
JD_MISSING_PENALTIES = (
    (0.7, 15.0),   # more than 70% of JD keywords absent
    (0.5, 10.0),
    (0.3, 5.0),
)

SUPABASE_URL       = os.getenv('SUPABASE_URL', '')
# Secret / service_role key. Bypasses row-level security, so it is server-side
# only and ownership is enforced by this code's own user_id filters.
SUPABASE_KEY       = os.getenv('SUPABASE_KEY', '')
SUPABASE_JWT_SECRET= os.getenv('SUPABASE_JWT_SECRET', '')   # used by backend to verify access tokens
GROQ_API_KEY       = os.getenv('GROQ_API_KEY', '')


