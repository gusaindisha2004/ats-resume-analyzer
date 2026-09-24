# ATS Resume Analyzer

Scores a resume the way an applicant tracking system would — and then does the
thing most resume tools skip: checks whether the skills you *claim* are
actually demonstrated anywhere in your projects or experience.

[![CI](https://github.com/gusaindisha2004/ats-resume-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/gusaindisha2004/ats-resume-analyzer/actions/workflows/ci.yml)

**Next.js 16 · React 19 · TypeScript · FastAPI · spaCy · Sentence Transformers · Groq · Supabase**

---

## The problem

Most applications are filtered by software before a person reads them. The
candidate never finds out why they were rejected, so they iterate blind.

The resume checkers that exist mostly count keywords and hand back a number
with no working. Worse, none of them check the claim that costs people
interviews: a Skills section listing twelve technologies, of which two appear
anywhere else in the document. A recruiter notices that in seconds.

This tool gives a score you can audit — every point traceable to a component,
every deduction explained — plus the specific edits that would move it.

## What it does

- **Scores out of 100** across five weighted components. The breakdown adds up
  to the total; there is no hidden maths between what you see and what you get.
- **Validates skills against evidence.** Every skill in your Skills section is
  matched against your project and experience text using sentence embeddings.
  Skills you can't back up are listed explicitly.
- **Matches against a job description** — fuzzy, alias-aware keyword overlap
  blended with semantic similarity.
- **Finds specific, fixable issues** — each with where it appears, why it costs
  you, concrete action items, and a rewritten example.
- **Checks writing quality** — spelling plus resume-specific style rules,
  filtered hard so technology names and British spellings aren't flagged.
- **Exports a PDF report** and keeps a history, so you can confirm a rewrite
  actually moved the number.

---

## How the analysis works

```
PDF / DOCX
    │
    ├─ pdfplumber (falls back to PyPDF2) ── also recovers embedded hyperlinks
    │                                        that plain text extraction drops
    ▼
raw text
    │
    ├─ Groq · openai/gpt-oss-120b ── structured JSON: skills, experience with
    │                                 durations, projects, action verbs, keywords
    ▼
parsed resume ──┬─ scoring (5 components, local)
                ├─ skill validation (sentence-transformers, local)
                ├─ JD matching (rapidfuzz + embeddings, local)
                ├─ writing checks (pyspellchecker + rules, local)
                └─ issue detection (rule-based, local)
                        │
                        ▼
                 score + explanation ── saved to Supabase
```

Only the parsing step leaves the machine. Everything after it runs locally.

### Why an LLM for parsing

A PDF gives you an unstructured wall of text. The scorer needs to know *this*
is a skill and *that* is a project description. Regex and spaCy alone do that
badly across the variety of real resume layouts — two columns, tables, headings
that aren't headings. The LLM does exactly one job: text in, structured JSON
out. The response is validated and type-coerced on the way back, and retried
once if it returns something unparseable.

### Score breakdown

Five components are scored directly on their point scales. **Those scales are
the weights**, and they sum to 100 — so the breakdown reconciles with the total.

| Component | Points | Why this weight |
| --- | --- | --- |
| Keywords & skills | 25 | An ATS screen is fundamentally keyword matching. Fail it and no human sees the resume. |
| Content quality | 25 | What a recruiter reads once past the filter: action verbs, quantified outcomes. |
| Formatting | 20 | A resume the parser mangles loses everything else — but modern parsers are tolerant, so it ranks below the two above. |
| Skill validation | 15 | Whether claimed skills are evidenced. A credibility signal a recruiter checks, not something an ATS scores. |
| ATS compatibility | 15 | Specific parser hazards: tables, box-drawing glyphs, street addresses. Narrow in scope. |

Small adjustments then apply to the total, each returned with a reason and
shown in the UI, so the gap between the component total and the headline number
is always accounted for:

```
Component total                                    78.0 / 100
Clean writing                                            +1.0
Missing job description keywords  (42% absent)           -8.0
Overall score                                            71.0
```

Grammar and location penalties are deliberately *not* in that list — they're
already subtracted inside the content and ATS-compatibility components, and
applying them again would punish one fault twice.

All of it lives in one place, `SCORE_WEIGHTS` in
[`backend/core/config.py`](backend/core/config.py), imported by the scorer and
by the API schema. A test asserts the five still sum to 100.

> **Where the numbers come from.** These weights are reasoned judgement calls,
> not values fitted to data. No public dataset of "resumes that passed an ATS"
> exists to calibrate against, and inventing one would be worse than admitting
> the gap. Treat the score as a consistent rubric for comparing drafts of the
> same resume, not a prediction of what any particular ATS will do.

### Skill validation

The distinguishing feature. For each skill in the Skills section, the analyzer
looks for evidence in the project and experience text — first a literal match,
then cosine similarity between sentence embeddings (`all-MiniLM-L6-v2`) above a
threshold.

The result separates skills backed by evidence — naming the project that
demonstrates each — from skills with none. Listing Kubernetes once in a Skills
section and never again is exactly what a recruiter probes in an interview.

### Job description matching

Two signals, deliberately combined:

- **Keyword overlap (60%)** — fuzzy matched with `rapidfuzz` and alias-aware, so
  `ReactJS`, `React.js` and `react` count as one thing. This is what an ATS
  actually does.
- **Semantic similarity (40%)** — cosine similarity of whole-document
  embeddings, which catches a resume describing the right work in different
  words.

The output separates **matched keywords**, **missing keywords** (shown in the
posting's own wording, so you know what to add), and a **skills gap** taken
from the required and preferred skills the LLM extracted from the posting.

Both lists are filtered first. Asked for keywords, a model will return
requirement sentences — *"Bachelor's degree in Statistics, Mathematics, ... or
related field"* — and the hiring company's own name. Neither can ever match a
resume term, so each one inflates the missing count and pushes the score
penalty up. A real posting was showing 92% of its terms as missing largely for
this reason.

### Resume quality checks

A general-purpose grammar checker is the wrong tool here. Resume bullets are
deliberate sentence fragments with no subject and no articles, so a conventional
checker floods the output with false positives on text that is correctly written
for its genre. Instead:

- **Spelling**, filtered hard. camelCase product names (`FastAPI`,
  `PostgreSQL`), acronyms, tokens with digits, URLs and their paths,
  spaCy-detected entities, a technology vocabulary, and the candidate's own
  listed skills are all excluded. British spellings are resolved to their US
  variants before flagging, so `optimised` and `containerised` pass.
- **Resume-specific style** — first-person pronouns, duty-style bullet openers
  ("Responsible for…"), duplicated words, spacing and capitalisation.

Findings are graded critical / moderate / minor and feed the content score.

### PDF reports

Jinja2 templates rendered to PDF with WeasyPrint, covering the summary, skills,
action items, and the JD comparison when one was supplied. WeasyPrint needs
native libraries (GTK/Pango/cairo); when they're missing the API returns a
**503 with installation instructions** rather than an opaque 500. They're
installed in the Docker image, so this works in deployment.

---

## Tech stack

| Layer | Choice |
| --- | --- |
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind v4 |
| Backend | FastAPI, Pydantic v2, Uvicorn |
| NLP | spaCy `en_core_web_md`, Sentence Transformers `all-MiniLM-L6-v2`, rapidfuzz |
| LLM | Groq (`openai/gpt-oss-120b`, configurable) |
| Auth & data | Supabase (Postgres + Auth, SSR cookie sessions) |
| Parsing | pdfplumber, PyPDF2, python-docx |
| Reports | Jinja2 + WeasyPrint |
| Testing | pytest, Vitest, Testing Library |
| CI | GitHub Actions |

## Architecture

```
├── backend/                FastAPI service
│   ├── api/                Routes and Supabase JWT verification
│   ├── core/               Config (scoring weights), rate limiting
│   ├── services/           Parsing, LLM extraction, scoring, writing checks, reports
│   ├── models/             Pydantic schemas — the API contract
│   ├── database/           Supabase REST persistence
│   ├── templates/          Jinja2 report templates
│   └── tests/              252 tests
├── web/                    Next.js frontend
│   └── src/
│       ├── app/            Routes: landing, analyze, history, login, auth callback
│       ├── components/     Score gauge, breakdown, issue list, panels
│       └── lib/            Typed API client, Supabase SSR clients, utilities
├── scripts/                Setup checker and database schema
├── deploy/                 Deployment guide and Hugging Face Space config
└── Dockerfile              Backend image (built in CI)
```

**Request flow:** the browser sends the file plus its Supabase access token →
FastAPI verifies the JWT (ES256/RS256 via JWKS, or HS256) → the file is
validated by content signature, not extension → text extraction → Groq returns
structured JSON → scoring, skill validation, JD matching and writing checks run
locally → the result is saved to Supabase and returned.

Models load once at startup into `app.state`, not per request.

The Pydantic schemas are the single source of truth for the API contract;
`web/src/lib/types.ts` mirrors them field for field.

---

## Running it locally

**Prerequisites:** Python 3.10+, Node 20+, a free [Groq API key](https://console.groq.com),
and a free [Supabase](https://supabase.com) project.

### 1. Backend

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
python -m spacy download en_core_web_md
cp .env.example .env              # then fill in your keys
uvicorn backend.main:app --reload --port 8000
```

API docs at http://localhost:8000/docs.

### 2. Frontend

```bash
cd web
npm install
cp .env.local.example .env.local  # then fill in your Supabase values
npm run dev
```

App at http://localhost:3000.

### 3. Database

Paste [`scripts/schema.sql`](scripts/schema.sql) into the Supabase SQL editor
(**SQL Editor → New query → Run**). It creates the `analyses` table, its index,
and the row-level-security policy. Re-running it is safe.

Then turn **off** Authentication → Providers → Email → *Confirm email* if you
want sign-up to log you straight in rather than emailing a link.

### 4. Verify the setup

```bash
python scripts/check_setup.py
```

Checks that every credential is present, that Groq accepts your key, that the
configured model is one your key can use, that Supabase is reachable, and that
the `analyses` table exists. It reports what is wrong and where to fix it, and
never prints a secret.

### Environment variables

**`.env`** (backend):

| Variable | Required | Purpose |
| --- | --- | --- |
| `SUPABASE_URL` | yes | Project URL; also used to fetch JWKS for token verification |
| `SUPABASE_KEY` | yes | **Secret** / service_role key. Bypasses RLS — server-side only |
| `SUPABASE_JWT_SECRET` | no | Only if your project still issues HS256 access tokens |
| `GROQ_API_KEY` | yes | Resume parsing is LLM-backed; there is no degraded mode |
| `GROQ_MODEL` | no | Defaults to `openai/gpt-oss-120b` |
| `ALLOWED_ORIGINS` | no | Comma-separated CORS origins, no trailing slash |
| `RATE_LIMIT_*` | no | See [Rate limits](#rate-limits) |

**`web/.env.local`** (frontend — everything here ships to the browser):

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | Same project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | **Publishable** / anon key — never the secret one |
| `NEXT_PUBLIC_API_URL` | Backend base URL |

## Using it

1. Sign up or sign in. Google sign-in appears only if the provider is enabled on
   your Supabase project — the login page queries `/auth/v1/settings` rather
   than offering a button that can't work.
2. Upload a resume (PDF or DOCX, max 5 MB). Type is determined by file
   signature, so renaming something to `.pdf` won't get it through.
3. Optionally paste a job posting to unlock match analysis.
4. Read the breakdown: where points came from, what to fix, which skills you
   can't back up, and what the posting wants that you're missing.
5. Export a PDF, or revisit past analyses in History.

## Rate limits

The analyze endpoint spends Groq tokens and several seconds of CPU, so it's
limited per caller — by authenticated user where there is one, falling back to
client IP (honouring `X-Forwarded-For`, since behind a proxy every request
otherwise shares one address).

| Endpoint | Default | Variable |
| --- | --- | --- |
| `POST /analyze-resume` | 10/hour | `RATE_LIMIT_ANALYZE` |
| PDF report endpoints | 30/hour | `RATE_LIMIT_REPORTS` |
| everything else | 120/minute | `RATE_LIMIT_DEFAULT` |

`RATE_LIMIT_ENABLED=false` turns it off. Storage is in-process, which is right
for a single container; point `RATE_LIMIT_STORAGE_URI` at Redis to share
counters across replicas.

## Testing

```bash
pytest backend/tests -q          # 252 tests
npm test --prefix web            # 57 tests
```

Both run on every push via [GitHub Actions](.github/workflows/ci.yml), along
with typecheck, lint, a production build, and a Docker image build.

**Backend (252)** — the HTTP layer via `TestClient` (auth including expiry and
misconfiguration, upload validation, status codes); file validation by
signature, including a renamed executable and a non-Word ZIP that must both be
rejected; every scoring component and its bounds; that the breakdown reconciles
and no penalty is counted twice; skill validation; location detection; writing
checks, most of which assert what must *not* be flagged; LLM response handling
(malformed JSON, markdown fences, retries, type coercion); rate limiting;
keyword hygiene, built from strings a real analysis actually produced; and a
full pipeline run against the real spaCy and sentence-transformer models with
only the Groq call mocked.

**Frontend (57)** — the score gauge and its accessible name, issue grouping and
expansion, the writing-quality panel, upload validation through both the file
picker and drag-and-drop, OAuth provider detection, and the normaliser that
keeps an older stored analysis from blanking the page.

## Deploying

Frontend on Vercel, backend on Hugging Face Spaces — both free tiers, both
behind a custom subdomain. Spaces is the deliberate choice for the backend: it
needs ~1 GB of RAM resident for spaCy and the sentence-transformer, more than
most free tiers allow, and Spaces gives 16 GB on free CPU.

See [`deploy/DEPLOY.md`](deploy/DEPLOY.md) for the walkthrough, DNS records and
Supabase redirect configuration.

## Limitations

- **Resume text is sent to Groq.** It's a third-party API, and the UI says so.
- **The Groq key is required** — the parser is LLM-backed, so there's no
  degraded mode without it.
- **Scoring weights are heuristics, not calibrated values** — see
  [Score breakdown](#score-breakdown).
- **Spelling has a residual false-positive rate.** Invented company names and
  niche jargon are occasionally flagged. Suppressing them entirely would also
  suppress real typos in headings, which is the worse trade.
- **Writing checks are spelling and resume style, not full grammar.**
- **Legacy `.doc` is unsupported** — convert to `.docx` or PDF.
- **Scanned PDFs fail.** There's no OCR; the error says so rather than
  returning an empty analysis.
- **PDF export needs native libraries.** Present in the Docker image; on a bare
  Windows machine the endpoint returns 503 with instructions.

## Possible next steps

- Calibrate the scoring weights against labelled outcome data, if a credible
  dataset can be assembled.
- OCR fallback for scanned PDFs via Tesseract.
- Make the LLM parser provider-pluggable, so it can run fully locally via Ollama.
- Rewrite suggestions for individual bullet points rather than section-level
  guidance.

## Licence

[MIT](LICENSE)
