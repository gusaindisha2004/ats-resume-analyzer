-- ATS Resume Analyzer — database schema.
--
-- Paste this whole file into the Supabase SQL editor
-- (Dashboard -> SQL Editor -> New query -> Run).
-- Safe to re-run: every statement is idempotent.

create table if not exists public.analyses (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users on delete cascade,
  filename    text not null,
  ats_score   real not null default 0,
  analysis    jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);

-- History is always read newest-first for one user.
create index if not exists analyses_user_created_idx
  on public.analyses (user_id, created_at desc);

-- The backend talks to PostgREST with the service_role key, which bypasses RLS
-- and scopes every query by user_id itself. RLS still matters: it means the
-- anon key (which ships to the browser) can never read anyone else's rows.
alter table public.analyses enable row level security;

drop policy if exists "users manage their own analyses" on public.analyses;
create policy "users manage their own analyses"
  on public.analyses
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
