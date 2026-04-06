"""Fun stats service — collect pilot statistics and generate humorous AI commentary."""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

import requests
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_API_KEY
from backend.models.flight import Flight

logger = logging.getLogger(__name__)

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Only free models — zero cost to the service operator.
# `openrouter/free` is a meta-model: OR auto-selects from available free providers.
# The explicit list is the fallback chain if the meta-model itself is unavailable.
# Many Venice-hosted models return 429; prefer non-Venice providers (openai/gpt-oss-*,
# stepfun, gemma variants) which have their own rate limit pools.
_FUN_STATS_MODELS = [
    "openrouter/free",
    "openai/gpt-oss-120b:free",
    "openai/gpt-oss-20b:free",
    "google/gemma-3-12b-it:free",
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "meta-llama/llama-3.2-3b-instruct:free",
]


# ---------------------------------------------------------------------------
# Stats collection
# ---------------------------------------------------------------------------

def collect_pilot_stats(db: Session, user_id: uuid.UUID) -> dict:
    """Collect aggregate flight statistics for a pilot from the database."""

    base_q = db.query(Flight).filter(Flight.user_id == user_id)

    # Basic aggregates
    agg = db.query(
        func.count(Flight.id).label('total_flights'),
        func.coalesce(func.sum(Flight.flight_time_min), 0).label('total_minutes'),
        func.coalesce(func.sum(Flight.price), 0).label('total_cost'),
        func.max(Flight.flight_time_min).label('longest_min'),
        func.min(Flight.flight_time_min).label('shortest_min'),
        func.count(func.distinct(Flight.date)).label('flight_days'),
    ).filter(Flight.user_id == user_id).one()

    total_flights = int(agg.total_flights or 0)
    total_minutes = int(agg.total_minutes or 0)

    # Date of longest flight
    longest_row = base_q.filter(
        Flight.flight_time_min == agg.longest_min,
        Flight.flight_time_min.isnot(None),
    ).order_by(Flight.date.asc()).first()
    longest_date = longest_row.date.isoformat() if longest_row and longest_row.date else '—'

    # Earliest takeoff time ever
    earliest_row = db.query(
        func.min(Flight.takeoff_time).label('earliest'),
    ).filter(Flight.user_id == user_id, Flight.takeoff_time.isnot(None)).one()
    earliest_takeoff = (
        earliest_row.earliest.strftime('%H:%M') if earliest_row.earliest else '—'
    )

    # Busiest day
    busiest = db.execute(text("""
        SELECT date, COUNT(*) AS cnt
        FROM flights
        WHERE user_id = :uid AND date IS NOT NULL
        GROUP BY date
        ORDER BY cnt DESC
        LIMIT 1
    """), {'uid': user_id}).fetchone()
    busiest_day_date = busiest[0].isoformat() if busiest else '—'
    busiest_day_flights = int(busiest[1]) if busiest else 0

    # Top winch operator (from raw_data JSONB)
    winch_row = db.execute(text("""
        SELECT raw_data->'crew'->>'winch_operator' AS operator, COUNT(*) AS cnt
        FROM flights
        WHERE user_id = :uid
          AND raw_data->'crew'->>'winch_operator' IS NOT NULL
          AND raw_data->'crew'->>'winch_operator' <> ''
        GROUP BY operator
        ORDER BY cnt DESC
        LIMIT 1
    """), {'uid': user_id}).fetchone()
    top_winch_operator = winch_row[0] if winch_row else '—'
    top_winch_count = int(winch_row[1]) if winch_row else 0

    # Main instructor (highest flight count with non-null instructor)
    instructor_row = db.execute(text("""
        SELECT instructor, COUNT(*) AS cnt
        FROM flights
        WHERE user_id = :uid AND instructor IS NOT NULL AND instructor <> ''
        GROUP BY instructor
        ORDER BY cnt DESC
        LIMIT 1
    """), {'uid': user_id}).fetchone()
    main_instructor = instructor_row[0] if instructor_row else '—'
    instructor_flights = int(instructor_row[1]) if instructor_row else 0

    # Total wait time between flights on the same day (minutes)
    wait_result = db.execute(text("""
        WITH ordered AS (
            SELECT date,
                   takeoff_time,
                   landing_time,
                   LAG(landing_time) OVER (PARTITION BY user_id, date ORDER BY takeoff_time) AS prev_landing
            FROM flights
            WHERE user_id = :uid
              AND takeoff_time IS NOT NULL
              AND landing_time IS NOT NULL
        )
        SELECT COALESCE(SUM(
            EXTRACT(EPOCH FROM (takeoff_time - prev_landing)) / 60
        ), 0) AS wait_minutes
        FROM ordered
        WHERE prev_landing IS NOT NULL
          AND takeoff_time > prev_landing
    """), {'uid': user_id}).fetchone()
    total_wait_minutes = int(wait_result[0] if wait_result else 0)
    total_wait_hours = round(total_wait_minutes / 60, 1)

    # Longest gap between consecutive flight dates
    gap_result = db.execute(text("""
        WITH dates AS (
            SELECT DISTINCT date FROM flights
            WHERE user_id = :uid AND date IS NOT NULL
            ORDER BY date
        ),
        gaps AS (
            SELECT date - LAG(date) OVER (ORDER BY date) AS gap
            FROM dates
        )
        SELECT COALESCE(MAX(gap), 0) AS max_gap FROM gaps
    """), {'uid': user_id}).fetchone()
    longest_gap_days = int(gap_result[0] if gap_result else 0)

    return {
        'total_hours':          total_minutes // 60,
        'total_minutes':        total_minutes % 60,
        'total_flights':        total_flights,
        'total_cost':           float(agg.total_cost or 0),
        'longest_flight_min':   int(agg.longest_min or 0),
        'longest_flight_date':  longest_date,
        'shortest_flight_min':  int(agg.shortest_min or 0),
        'top_winch_operator':   top_winch_operator,
        'top_winch_count':      top_winch_count,
        'main_instructor':      main_instructor,
        'instructor_flights':   instructor_flights,
        'earliest_takeoff':     earliest_takeoff,
        'busiest_day_date':     busiest_day_date,
        'busiest_day_flights':  busiest_day_flights,
        'total_wait_hours':     total_wait_hours,
        'flight_days':          int(agg.flight_days or 0),
        'longest_gap_days':     longest_gap_days,
    }


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_fun_stats_prompt(stats: dict, language: str = 'pl') -> str:
    lang_instruction = {
        'pl': 'po polsku',
        'en': 'in English',
        'de': 'auf Deutsch',
        'cs': 'v češtině',
    }.get(language, 'po polsku')

    return (
        f"Jesteś humorystycznym komentatorem lotów szybowcowych.\n"
        f"Na podstawie poniższych danych pilota wygeneruj dokładnie 8 śmiesznych,\n"
        f"ciepłych i spersonalizowanych statystyk {lang_instruction}. Każda statystyka powinna\n"
        f"mieć: tytuł (max 5 słów), wartość liczbową lub frazę, oraz jedno zdanie\n"
        f"komentarza z humorem. Używaj konkretnych liczb z danych. Bądź ciepły,\n"
        f"nie złośliwy. Nawiązuj do realiów szybownictwa.\n\n"
        f"Dane pilota:\n"
        f"- Łączny nalot: {stats['total_hours']}h {stats['total_minutes']}min\n"
        f"- Liczba lotów: {stats['total_flights']}\n"
        f"- Łączny koszt sezonu: {stats['total_cost']} zł\n"
        f"- Najdłuższy lot: {stats['longest_flight_min']} min ({stats['longest_flight_date']})\n"
        f"- Najkrótszy lot: {stats['shortest_flight_min']} min\n"
        f"- Ulubiony wyciągarkowy: {stats['top_winch_operator']} ({stats['top_winch_count']} startów)\n"
        f"- Główny instruktor: {stats['main_instructor']} ({stats['instructor_flights']} lotów)\n"
        f"- Najwcześniejszy start: {stats['earliest_takeoff']}\n"
        f"- Najpracowszy dzień: {stats['busiest_day_date']} ({stats['busiest_day_flights']} lotów)\n"
        f"- Łączny czas oczekiwania między lotami tego samego dnia: {stats['total_wait_hours']}h\n"
        f"- Liczba dni lotnych: {stats['flight_days']}\n"
        f"- Najdłuższa przerwa między lotami: {stats['longest_gap_days']} dni\n\n"
        f"Odpowiedz TYLKO w formacie JSON (bez markdown):\n"
        f'{{"stats": [{{"title": "...", "value": "...", "comment": "..."}}, ...]}}'
    )


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

def _parse_json_response(text: str) -> list:
    """Extract the stats list from an LLM JSON response, stripping markdown if needed."""
    cleaned = text.strip()
    # Strip ```json ... ``` fences if present
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    cleaned = cleaned.strip()
    data = json.loads(cleaned)
    return data['stats']


# ---------------------------------------------------------------------------
# OpenRouter call
# ---------------------------------------------------------------------------

def generate_fun_stats(
    stats: dict,
    language: str = 'pl',
    api_key: Optional[str] = None,
) -> tuple[list, str]:
    """Generate humorous stats via OpenRouter. Returns (stats_list, model_used).

    Strategy:
    1. Try openrouter/free (meta-model, OR auto-selects an available free provider).
    2. On failure, try the explicit model list with OR's route:fallback in one request.
    Returns ([], '') on total failure.
    """
    key = api_key or OPENROUTER_API_KEY
    if not key:
        logger.warning('fun_stats: no OpenRouter API key available, skipping generation')
        return [], ''

    prompt = build_fun_stats_prompt(stats, language)

    def _call(body: dict) -> tuple[list, str]:
        logger.info('fun_stats: calling OpenRouter model=%s', body['model'])
        resp = requests.post(
            _OPENROUTER_URL,
            headers={
                'Authorization':      f'Bearer {key}',
                'HTTP-Referer':       'https://soaring-cup.com',
                'X-OpenRouter-Title': 'GlideLog Fun Stats',
                'Content-Type':       'application/json',
            },
            json=body,
            timeout=30,
        )
        if not resp.ok:
            logger.error('fun_stats: OpenRouter HTTP %d: %s', resp.status_code, resp.text[:500])
        resp.raise_for_status()
        data = resp.json()
        raw_text = data['choices'][0]['message']['content']
        model_used = data.get('model', body['model'])
        short_model = model_used.split('/')[-1] if '/' in model_used else model_used
        result = _parse_json_response(raw_text)
        logger.info('fun_stats: generated via %s', model_used)
        return result, short_model

    # Attempt 1: openrouter/free meta-model
    try:
        return _call({
            'model':       'openrouter/free',
            'messages':    [{'role': 'user', 'content': prompt}],
            'temperature': 0.9,
            'max_tokens':  2048,
        })
    except Exception:
        logger.warning('fun_stats: openrouter/free failed, trying explicit model list', exc_info=True)

    # Attempt 2: explicit free model list with OR fallback routing
    explicit_models = _FUN_STATS_MODELS[1:]  # skip openrouter/free
    try:
        return _call({
            'model':       explicit_models[0],
            'models':      explicit_models,
            'route':       'fallback',
            'messages':    [{'role': 'user', 'content': prompt}],
            'temperature': 0.9,
            'max_tokens':  2048,
        })
    except Exception:
        logger.error('fun_stats: all attempts failed', exc_info=True)
        return [], ''


# ---------------------------------------------------------------------------
# Cache upsert
# ---------------------------------------------------------------------------

def upsert_cache(
    db: Session,
    user_id: uuid.UUID,
    content: list,
    model_used: str,
) -> None:
    """Insert or update the fun_stats_cache row for a user."""
    from backend.models.fun_stats_cache import FunStatsCache  # local to avoid circular

    now = datetime.now(timezone.utc)
    existing = db.query(FunStatsCache).filter_by(user_id=user_id).first()
    if existing:
        existing.content = content
        existing.generated_at = now
        existing.model_used = model_used
    else:
        db.add(FunStatsCache(
            user_id=user_id,
            generated_at=now,
            content=content,
            model_used=model_used,
        ))
    db.commit()
