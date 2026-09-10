"""Supabase persistence for saved analyses.

Uses the Supabase REST API with the service_role key, which bypasses row-level
security. Ownership is therefore enforced here, in the `user_id=eq.` filter on
every query — never drop it.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from backend.core.config import SUPABASE_KEY, SUPABASE_URL
from backend.models.schemas import AnalysisResponse, HistoryEntry

logger = logging.getLogger('ats_resume_scorer')

_TABLE = 'analyses'
_TIMEOUT = httpx.Timeout(10.0)


def _endpoint() -> str:
    return f"{SUPABASE_URL.rstrip('/')}/rest/v1/{_TABLE}"


def _headers(prefer: str = 'return=representation') -> Optional[Dict[str, str]]:
    """Auth headers, or None when Supabase isn't configured (history is then a no-op)."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': prefer,
    }


def _to_history_entry(row: Dict[str, Any]) -> HistoryEntry:
    analysis = row.get('analysis') or {}
    jd_match = analysis.get('jd_match') or {}
    return HistoryEntry(
        id=str(row.get('id')),
        filename=row.get('filename') or 'resume',
        ats_score=row.get('ats_score') or 0.0,
        jd_match_percentage=jd_match.get('match_percentage'),
        created_at=row.get('created_at'),
        analysis=analysis,
    )


async def save_analysis(user_id: str, analysis: AnalysisResponse) -> Optional[str]:
    """Persist one analysis. Returns the new row id, or None if it wasn't saved."""
    headers = _headers()
    if headers is None:
        logger.info('Supabase not configured — skipping history save')
        return None

    payload = analysis.model_dump(mode='json')
    row = {
        'user_id': user_id,
        'filename': analysis.filename,
        'ats_score': analysis.ats_score,
        'created_at': payload['analyzed_at'],
        'analysis': payload,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(_endpoint(), headers=headers, json=row)
        response.raise_for_status()
        data = response.json()

    if not data:
        return None
    saved_id = str(data[0].get('id'))
    logger.info(f'Saved analysis {saved_id} for user {user_id}')
    return saved_id


async def get_user_history(user_id: str) -> List[HistoryEntry]:
    headers = _headers()
    if headers is None:
        return []

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.get(
            _endpoint(),
            headers=headers,
            params={'user_id': f'eq.{user_id}', 'order': 'created_at.desc'},
        )
        response.raise_for_status()
        rows = response.json()

    return [_to_history_entry(row) for row in rows]


async def get_analysis(analysis_id: str, user_id: str) -> Optional[HistoryEntry]:
    """Fetch a single analysis, scoped to its owner."""
    headers = _headers()
    if headers is None:
        return None

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.get(
            _endpoint(),
            headers=headers,
            params={'id': f'eq.{analysis_id}', 'user_id': f'eq.{user_id}', 'limit': 1},
        )
        response.raise_for_status()
        rows = response.json()

    return _to_history_entry(rows[0]) if rows else None


async def delete_analysis(analysis_id: str, user_id: str) -> bool:
    """Delete one analysis. Returns False when no row matched — i.e. wrong id or
    not the caller's row — so the route can answer 404 instead of a false 200."""
    headers = _headers()
    if headers is None:
        return False

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.delete(
            _endpoint(),
            headers=headers,
            params={'id': f'eq.{analysis_id}', 'user_id': f'eq.{user_id}'},
        )
        response.raise_for_status()
        deleted_rows = response.json()

    return bool(deleted_rows)
