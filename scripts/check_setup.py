"""Verify local configuration before running the app.

Checks every credential the app needs and tells you exactly what is missing and
where to fix it. Secrets are never printed — only whether they are present and
whether they work.

    python scripts/check_setup.py
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GREEN, RED, YELLOW, DIM, RESET = '\033[32m', '\033[31m', '\033[33m', '\033[2m', '\033[0m'
if os.name == 'nt' and not os.environ.get('WT_SESSION'):
    try:  # enable ANSI on older Windows consoles
        import ctypes

        ctypes.windll.kernel32.SetConsoleMode(
            ctypes.windll.kernel32.GetStdHandle(-11), 7
        )
    except Exception:
        GREEN = RED = YELLOW = DIM = RESET = ''

PLACEHOLDERS = ('your-', 'placeholder', 'xxx', 'changeme')

results: list[tuple[bool, str]] = []


def report(ok: bool, label: str, detail: str = '', fix: str = '') -> bool:
    mark = f'{GREEN}PASS{RESET}' if ok else f'{RED}FAIL{RESET}'
    print(f'  [{mark}] {label}')
    if detail:
        print(f'         {DIM}{detail}{RESET}')
    if not ok and fix:
        print(f'         {YELLOW}-> {fix}{RESET}')
    results.append((ok, label))
    return ok


def is_set(value: str | None) -> bool:
    if not value or not value.strip():
        return False
    return not any(p in value.lower() for p in PLACEHOLDERS)


def load_env_files() -> dict:
    """Read .env and web/.env.local without needing python-dotenv."""
    values = {}
    for path in (ROOT / '.env', ROOT / 'web' / '.env.local'):
        if not path.exists():
            continue
        for raw in path.read_text(encoding='utf-8').splitlines():
            line = raw.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, val = line.partition('=')
            # strip trailing inline comments and quotes
            val = val.split('#')[0].strip().strip('"').strip("'")
            values[key.strip()] = val
    return values


def main() -> int:
    env = load_env_files()

    print(f'\n{DIM}Reading .env and web/.env.local{RESET}\n')

    # ---- 1. Files exist -----------------------------------------------
    print('Configuration files')
    report(
        (ROOT / '.env').exists(),
        'backend .env exists',
        fix='cp .env.example .env',
    )
    report(
        (ROOT / 'web' / '.env.local').exists(),
        'frontend web/.env.local exists',
        fix='cp web/.env.local.example web/.env.local',
    )

    # ---- 2. Groq ------------------------------------------------------
    print('\nGroq (resume parsing — required)')
    groq_key = env.get('GROQ_API_KEY', '')
    if report(
        is_set(groq_key),
        'GROQ_API_KEY is set',
        fix='Get a free key at https://console.groq.com and put it in .env',
    ):
        try:
            import httpx

            response = httpx.get(
                'https://api.groq.com/openai/v1/models',
                headers={'Authorization': f'Bearer {groq_key}'},
                timeout=15,
            )
            report(
                response.status_code == 200,
                'Groq key is accepted',
                f'HTTP {response.status_code}',
                fix='The key was rejected. Check for a typo or a revoked key.',
            )
        except Exception as exc:
            report(False, 'Groq reachable', str(exc)[:80], fix='Check your connection.')

    # ---- 3. Supabase credentials --------------------------------------
    print('\nSupabase (auth + saved history)')
    url = env.get('SUPABASE_URL', '')
    service_key = env.get('SUPABASE_KEY', '')
    url_front = env.get('NEXT_PUBLIC_SUPABASE_URL', '')
    anon_front = env.get('NEXT_PUBLIC_SUPABASE_ANON_KEY', '')

    have_url = report(
        is_set(url), 'SUPABASE_URL is set (.env)',
        fix='Dashboard -> Project Settings -> API -> Project URL',
    )
    have_service = report(
        is_set(service_key), 'SUPABASE_KEY (secret) is set (.env)',
        fix='Dashboard -> Project Settings -> API -> Secret keys -> New secret key',
    )
    report(
        is_set(url_front), 'NEXT_PUBLIC_SUPABASE_URL is set (web/.env.local)',
        fix='Same Project URL as the backend',
    )
    report(
        is_set(anon_front), 'NEXT_PUBLIC_SUPABASE_ANON_KEY is set (web/.env.local)',
        fix='Dashboard -> Project Settings -> API -> Publishable key',
    )

    if is_set(url) and is_set(url_front):
        report(
            url.rstrip('/') == url_front.rstrip('/'),
            'Frontend and backend point at the same project',
            fix='SUPABASE_URL and NEXT_PUBLIC_SUPABASE_URL must match',
        )

    # ---- 4. Supabase connectivity + schema ----------------------------
    if have_url and have_service:
        import httpx

        base = url.rstrip('/')
        headers = {
            'apikey': service_key,
            'Authorization': f'Bearer {service_key}',
        }
        try:
            auth = httpx.get(f'{base}/auth/v1/health', timeout=15)
            report(
                auth.status_code < 500,
                'Supabase project is reachable',
                f'HTTP {auth.status_code}',
                fix='Check the URL, or whether the project is paused.',
            )
        except Exception as exc:
            report(False, 'Supabase reachable', str(exc)[:80],
                   fix='Check SUPABASE_URL and your connection.')

        try:
            table = httpx.get(
                f'{base}/rest/v1/analyses',
                headers=headers,
                params={'limit': 1},
                timeout=15,
            )
            if table.status_code == 200:
                report(True, "'analyses' table exists and is readable")
            elif table.status_code in (401, 403):
                report(False, "'analyses' table readable",
                       f'HTTP {table.status_code} — key rejected',
                       fix='Make sure SUPABASE_KEY is the service_role secret, not anon.')
            else:
                body = table.text[:120]
                report(False, "'analyses' table exists",
                       f'HTTP {table.status_code}: {body}',
                       fix='Run the SQL in README.md -> Database in the Supabase SQL editor.')
        except Exception as exc:
            report(False, "'analyses' table check", str(exc)[:80])

    # ---- 5. Summary ---------------------------------------------------
    passed = sum(1 for ok, _ in results if ok)
    total = len(results)
    failed = [label for ok, label in results if not ok]

    print(f'\n{"-" * 58}')
    if not failed:
        print(f'{GREEN}All {total} checks passed — the full flow should work.{RESET}')
        print(f'\n{DIM}Start it with:{RESET}')
        print('  uvicorn backend.main:app --reload --port 8000')
        print('  npm run dev --prefix web')
        return 0

    print(f'{RED}{len(failed)} of {total} checks failed:{RESET}')
    for label in failed:
        print(f'  - {label}')
    print(f'\n{DIM}Fix the items marked -> above, then run this again.{RESET}')
    return 1


if __name__ == '__main__':
    sys.exit(main())
