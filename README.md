# ATS Resume Analyzer

Scores a resume the way an applicant tracking system would, and — the part most
tools skip — checks whether the skills you claim are actually demonstrated
anywhere in your projects or experience.

[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)

**Next.js 16 · React 19 · TypeScript · FastAPI · spaCy · Sentence Transformers · Groq · Supabase**

---

## What it does

Upload a PDF or DOCX resume, optionally paste a job posting, and get back:

- **An overall ATS score out of 100**, broken into five weighted components.
- **Skill validation** — every skill in your Skills section is matched against
  your project and experience text using sentence embeddings. Skills you can't
  back up are listed explicitly, because a recruiter will notice them too.
- **Job description matching** — keyword overlap (fuzzy-matched, alias-aware, so
  `ReactJS` and `React.js` count as the same thing) blended with semantic
  similarity from the embedding model.
- **Specific issues**, each with where it appears, why it costs you, concrete
  action items, and a rewritten example.
- **Writing quality** — spelling plus resume-specific style rules (first-person
  pronouns, duty-style bullet openers, duplicated words). Technology names,
  acronyms, URLs, your own listed skills and British spellings are all excluded,
  so the section stays worth reading.
- **A PDF report** and a saved history, so you can check a rewrite actually
  moved the number.

## How the score works

The five components are scored on their own scales, converted to percentages,
then re-weighted into the final number:

| Component         | Raw scale | Weight in final score      |
| ----------------- | --------- | -------------------------- |
| Keywords & skills | /25       | 40% combined with          |
| Skill validation  | /15       | ↳ (keywords 60 / skills 40) |
| Content quality   | /25       | 30%                        |
| Formatting        | /20       | 15%                        |
| ATS compatibility | /15       | 15%                        |

Bonuses apply for high skill validation; penalties apply for privacy risks
(street addresses, ZIP codes) and for missing a large share of the job
description's keywords.

## Architecture

```
├── backend/            FastAPI service
│   ├── api/            Routes and Supabase JWT verification
│   ├── services/       Parsing, LLM extraction, scoring, writing checks, reports
│   ├── models/         Pydantic schemas — the API contract
│   ├── database/       Supabase REST persistence
│   └── tests/          191 tests, pytest
└── web/                Next.js App Router frontend
    ├── src/app/        Routes: landing, analyze, history, login, auth callback
    ├── src/components/ Score gauge, breakdown, issue list, panels
    └── src/lib/        Typed API client, Supabase SSR clients, utilities
```

**Request flow:** the browser sends the file plus the Supabase access token →
FastAPI verifies the JWT (ES256/RS256 via JWKS, or HS256) → `pdfplumber`
extracts text, falling back to `PyPDF2`, and pulls out embedded hyperlinks that
plain extraction drops → Groq's `llama-3.3-70b-versatile` returns structured
JSON → scoring, skill validation and JD matching run locally → the result is
saved to Supabase and returned.

Models load once at startup into `app.state` rather than per request.

## Running it locally

**Prerequisites:** Python 3.10+, Node 20+, a [Groq API key](https://console.groq.com)
(free), and a [Supabase](https://supabase.com) project (free).

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
(Dashboard → SQL Editor → New query → Run). It creates the `analyses` table,
its index, and the row-level-security policy. Re-running it is safe.

### 4. Check the setup

```bash
python scripts/check_setup.py
```

Verifies every credential the app needs — that the keys are present, that Groq
accepts yours, that the Supabase project is reachable, and that the `analyses`
table exists. It prints what is wrong and where to fix it, and never prints a
secret.

## Tests

```bash
pytest backend/tests -q          # backend, 191 tests
npm test --prefix web            # frontend, 51 tests
```

Both run on every push via [GitHub Actions](.github/workflows/ci.yml), along
with typecheck, lint and a production build.

**Backend — 191 tests** covering:

- **HTTP layer** — auth (valid, malformed, expired, unconfigured), file upload,
  status codes, and the full response body, driven through `TestClient`.
- **File validation** — type detection by signature, including a renamed
  executable and a non-Word ZIP, both of which must be rejected.
- **Scoring** — every component and its bounds, aggregation, penalties.
- **Skill validation** and location/privacy detection.
- **Writing checks** — with heavy emphasis on what must *not* be flagged.
- **LLM response handling** — malformed JSON, markdown fences, retries, coercion.
- **Stored-analysis compatibility** — rows written by older versions still render.
- **Rate limiting** — per-caller identity, quota enforcement, and that one
  caller hitting the wall doesn't lock out everyone else.
- **Full pipeline** against the real spaCy and sentence-transformer models,
  with only the Groq call mocked.

**Frontend — 51 tests** (Vitest + Testing Library) covering the score gauge and
its accessible name, issue grouping and expansion, the writing-quality panel,
upload validation through both the picker and drag-and-drop, and the normaliser
that keeps an older stored analysis from blanking the page.

## Rate limits

The analyze endpoint spends Groq tokens and several seconds of CPU, so it is
limited per caller — by authenticated user where there is one, falling back to
client IP (honouring `X-Forwarded-For`, since behind a proxy every request
otherwise shares one address).

| Endpoint | Default | Env var |
| --- | --- | --- |
| `POST /analyze-resume` | 10/hour | `RATE_LIMIT_ANALYZE` |
| PDF report endpoints | 30/hour | `RATE_LIMIT_REPORTS` |
| everything else | 120/minute | `RATE_LIMIT_DEFAULT` |

Set `RATE_LIMIT_ENABLED=false` to turn it off. Storage is in-process, which is
right for a single container; point `RATE_LIMIT_STORAGE_URI` at Redis to share
counters across replicas.

## Notes and limitations

- **Resume text is sent to Groq.** It's a third-party API. The UI says so.
- **The Groq key is required** — the parser is LLM-backed, so there's no
  degraded mode without it.
- **PDF export needs native libraries.** WeasyPrint depends on GTK/Pango/cairo.
  Without them the API returns a 503 with instructions rather than failing
  opaquely. On Windows, install the GTK3 runtime; on Debian/Ubuntu:
  `sudo apt install libcairo2 libpango-1.0-0 libpangoft2-1.0-0 libffi-dev`.
- **Writing checks are spelling + resume style, not full grammar.** A
  general-purpose grammar checker is the wrong tool: resume bullets are
  deliberate sentence fragments, so a conventional checker floods the output
  with false positives on correctly-written text. See
  `backend/services/grammar_checker.py` for the reasoning and the filters.
- **Legacy `.doc` is unsupported** — convert to `.docx` or PDF first. File type
  is determined from the file's signature rather than its extension, so renaming
  something to `.pdf` won't get it through.
- **The scoring weights are heuristics, not calibrated values.** They were
  chosen to be reasonable, not derived from labelled outcome data, and no
  public dataset of "resumes that passed an ATS" exists to fit them against.
  Treat the score as a consistent rubric for comparing drafts of the same
  resume, not as a prediction of what any particular ATS will do.
