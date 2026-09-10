# ATS Resume Analyzer

Scores a resume the way an applicant tracking system would, and — the part most
tools skip — checks whether the skills you claim are actually demonstrated
anywhere in your projects or experience.

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
│   ├── services/       Parsing, LLM extraction, scoring, feedback, reports
│   ├── models/         Pydantic schemas — the API contract
│   ├── database/       Supabase REST persistence
│   └── tests/          75 tests, pytest
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

Create the `analyses` table in the Supabase SQL editor:

```sql
create table analyses (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users on delete cascade,
  filename    text not null,
  ats_score   real not null default 0,
  analysis    jsonb not null,
  created_at  timestamptz not null default now()
);

create index analyses_user_created_idx on analyses (user_id, created_at desc);

-- The backend uses the service_role key and scopes every query by user_id,
-- but RLS is enabled so the anon key can never read another user's rows.
alter table analyses enable row level security;

create policy "own rows" on analyses
  for all using (auth.uid() = user_id);
```

## Tests

```bash
pytest backend/tests -q
```

75 tests covering keyword matching and alias resolution, each scoring component
and its bounds, skill validation, location detection, LLM response handling
(malformed JSON, markdown fences, retries, type coercion), and a full pipeline
run against the real spaCy and sentence-transformer models with only the Groq
call mocked.

## Notes and limitations

- **Resume text is sent to Groq.** It's a third-party API. The UI says so.
- **The Groq key is required** — the parser is LLM-backed, so there's no
  degraded mode without it.
- **PDF export needs native libraries.** WeasyPrint depends on GTK/Pango/cairo.
  Without them the API returns a 503 with instructions rather than failing
  opaquely. On Windows, install the GTK3 runtime; on Debian/Ubuntu:
  `sudo apt install libcairo2 libpango-1.0-0 libpangoft2-1.0-0 libffi-dev`.
- **Grammar checking is not implemented.** The scorer accepts a grammar result
  and applies neutral defaults, so the hook exists but the check doesn't.
- **Legacy `.doc` is unsupported** — convert to `.docx` or PDF first.
- The `jupyter notebooks/` research (BERT fine-tuning on resume/JD pairs) informed
  the approach but the fine-tuned model isn't wired in; runtime uses stock
  `all-MiniLM-L6-v2`.
