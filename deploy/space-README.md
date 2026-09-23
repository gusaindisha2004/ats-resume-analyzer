---
title: ATS Resume Analyzer API
emoji: 🎯
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# ATS Resume Analyzer — API

FastAPI backend for the [ATS Resume Analyzer](https://github.com/gusaindisha2004/ats-resume-analyzer).
Parses a resume, scores it against five weighted components, validates claimed
skills against project evidence, and compares it to a job description.

Interactive API docs: **`/docs`**

## Required secrets

Set these in **Settings → Variables and secrets**:

| Name | Value |
| --- | --- |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase **secret** key (bypasses RLS — secret, not variable) |
| `GROQ_API_KEY` | Groq API key |
| `ALLOWED_ORIGINS` | The frontend origin, e.g. `https://ats.example.com` |
| `GROQ_MODEL` | Optional; defaults to `openai/gpt-oss-120b` |

`ALLOWED_ORIGINS` must have **no trailing slash** — CORS origin matching is
exact, and a trailing slash silently blocks every browser request.

## Notes

The spaCy model and the sentence-transformer are baked into the image, so a
cold start is model loading only (~20–40s) rather than a download.
