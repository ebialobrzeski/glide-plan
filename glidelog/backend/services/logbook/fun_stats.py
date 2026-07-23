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
from backend.models.user import User

logger = logging.getLogger(__name__)

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Preferred model — a stronger, more creative model than the free tier. Fun
# stats now run on the user's own OpenRouter key, so the (small) cost is theirs
# and it is worth a noticeably better result. If this call fails (no credit,
# provider down, …) we transparently fall back to the free models below.
_PRIMARY_FUN_STATS_MODEL = "deepseek/deepseek-chat"

# Free fallback models — zero cost, used only when the preferred model is
# unavailable so fun stats keep working even without paid credit.
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


# Cap on how many individual flight rows we hand to the model. Enough to give
# it rich material to mine for patterns while staying comfortably inside the
# context window of the free fallback models. When a pilot has more flights we
# send the most recent ones and tell the model the true total.
_MAX_FLIGHTS_FOR_PROMPT = 400


# ---------------------------------------------------------------------------
# Raw data collection
# ---------------------------------------------------------------------------

def collect_raw_flights(
    db: Session,
    user_id: uuid.UUID,
    limit: int = _MAX_FLIGHTS_FOR_PROMPT,
) -> dict:
    """Collect raw per-flight data for a pilot to hand to the LLM.

    Instead of pre-computing a fixed set of aggregates, we pull the raw flight
    log (most recent ``limit`` flights) plus a couple of headline totals for
    context, and let the model decide for itself which patterns are worth
    turning into fun stats. Returns a dict with:

    - ``total_flights`` — the pilot's true total flight count
    - ``included``      — how many flight rows are in ``flights`` (<= total)
    - ``totals``        — a few cheap aggregates for scale/context
    - ``flights``       — list of compact per-flight dicts, newest first
    """
    totals_row = db.query(
        func.count(Flight.id).label('total_flights'),
        func.coalesce(func.sum(Flight.flight_time_min), 0).label('total_minutes'),
        func.coalesce(func.sum(Flight.price), 0).label('total_cost'),
        func.count(func.distinct(Flight.date)).label('flight_days'),
    ).filter(Flight.user_id == user_id).one()

    total_flights = int(totals_row.total_flights or 0)
    total_minutes = int(totals_row.total_minutes or 0)

    rows = db.execute(text("""
        SELECT date,
               aircraft_type,
               aircraft_reg,
               launch_type,
               takeoff_airport,
               landing_airport,
               to_char(takeoff_time, 'HH24:MI')  AS takeoff,
               to_char(landing_time, 'HH24:MI')  AS landing,
               flight_time_min,
               landings,
               instructor,
               task,
               price,
               raw_data->'crew'->>'winch_operator' AS winch_operator
        FROM flights
        WHERE user_id = :uid
        ORDER BY date DESC NULLS LAST, takeoff_time DESC NULLS LAST
        LIMIT :lim
    """), {'uid': user_id, 'lim': limit}).mappings().all()

    flights = []
    for r in rows:
        flights.append({
            'date':           r['date'].isoformat() if r['date'] else None,
            'aircraft_type':  r['aircraft_type'],
            'aircraft_reg':   r['aircraft_reg'],
            'launch_type':    r['launch_type'],
            'takeoff_airport': r['takeoff_airport'],
            'landing_airport': r['landing_airport'],
            'takeoff_time':   r['takeoff'],
            'landing_time':   r['landing'],
            'flight_time_min': r['flight_time_min'],
            'landings':       r['landings'],
            'instructor':     r['instructor'],
            'task':           r['task'],
            'price':          float(r['price']) if r['price'] is not None else None,
            'winch_operator': r['winch_operator'],
        })

    return {
        'total_flights': total_flights,
        'included':      len(flights),
        'totals': {
            'total_hours':   total_minutes // 60,
            'total_minutes': total_minutes % 60,
            'total_cost':    float(totals_row.total_cost or 0),
            'flight_days':   int(totals_row.flight_days or 0),
        },
        'flights': flights,
    }


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

# Columns emitted in the CSV table, in order. Keeping this compact keeps the
# token count down while still giving the model everything it needs to spot
# patterns of its own.
_CSV_COLUMNS = [
    ('date',            'date'),
    ('aircraft_type',   'aircraft'),
    ('aircraft_reg',    'reg'),
    ('launch_type',     'launch'),
    ('takeoff_airport', 'from'),
    ('landing_airport', 'to'),
    ('takeoff_time',    'takeoff'),
    ('landing_time',    'landing'),
    ('flight_time_min', 'mins'),
    ('landings',        'landings'),
    ('instructor',      'instructor'),
    ('task',            'task'),
    ('price',           'price'),
    ('winch_operator',  'winch'),
]


def _flights_to_csv(flights: list) -> str:
    """Render flight dicts as a compact CSV block for the prompt."""
    def _cell(val) -> str:
        if val is None:
            return ''
        s = str(val)
        # Escape only what a naive CSV reader would trip on.
        if any(ch in s for ch in (',', '"', '\n')):
            s = '"' + s.replace('"', '""') + '"'
        return s

    header = ','.join(label for _, label in _CSV_COLUMNS)
    lines = [header]
    for f in flights:
        lines.append(','.join(_cell(f.get(key)) for key, _ in _CSV_COLUMNS))
    return '\n'.join(lines)


def build_fun_stats_prompt(data: dict, language: str = 'pl') -> str:
    """Build the LLM prompt from raw flight data.

    ``data`` is the dict returned by :func:`collect_raw_flights`. We hand the
    model the raw flight log and let it invent its own stats rather than feeding
    it pre-chewed aggregates.
    """
    lang_instruction = {
        'pl': 'in Polish (po polsku)',
        'en': 'in English',
        'de': 'in German (auf Deutsch)',
        'cs': 'in Czech (v češtině)',
    }.get(language, 'in Polish (po polsku)')

    totals = data.get('totals', {})
    total_flights = data.get('total_flights', 0)
    included = data.get('included', 0)

    scope_note = ''
    if included < total_flights:
        scope_note = (
            f"NOTE: this pilot has {total_flights} flights in total; only the "
            f"{included} most recent are listed below. Treat the totals line as "
            f"the source of truth for career-wide figures.\n\n"
        )

    csv_block = _flights_to_csv(data.get('flights', []))

    return (
        "You are a witty, warm commentator on glider flying. You are given a "
        "pilot's raw flight log. Study the data, find the funny, surprising, "
        "endearing or oddly specific patterns hiding in it, and invent your own "
        "fun statistics from what you discover.\n\n"
        f"Generate exactly 8 fun stats, written {lang_instruction}. Make each one "
        "genuinely derived from THIS pilot's data — pick different angles "
        "(favourite aircraft, launch habits, airfields, timing quirks, loyal "
        "winch operators or instructors, marathon days, dry spells, money spent, "
        "landing counts, whatever the numbers suggest). Do not just restate a "
        "single obvious total eight times; be creative and varied.\n\n"
        "Each stat must have:\n"
        "- title: a short punchy label (max 5 words)\n"
        "- value: a number or short phrase (the headline figure)\n"
        "- comment: one warm, funny sentence. Reference real gliding culture. "
        "Be kind, never mean.\n\n"
        "Always compute values yourself from the data below — do not make up "
        "numbers that the data does not support.\n\n"
        f"Pilot totals (career-wide): {total_flights} flights, "
        f"{totals.get('total_hours', 0)}h {totals.get('total_minutes', 0)}min "
        f"airborne, {totals.get('flight_days', 0)} flying days, "
        f"{totals.get('total_cost', 0)} zł spent.\n\n"
        f"{scope_note}"
        "Flight log (CSV; times HH:MM, mins = flight minutes, launch e.g. "
        "winch/aerotow, price in zł):\n"
        f"{csv_block}\n\n"
        "Respond with ONLY JSON (no markdown, no prose):\n"
        '{"stats": [{"title": "...", "value": "...", "comment": "..."}, ...]}'
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
# API key resolution
# ---------------------------------------------------------------------------

def resolve_api_key(db: Session, user_id: uuid.UUID) -> Optional[str]:
    """Return the OpenRouter API key to use for a user's fun-stats generation.

    Preference order:
    1. The user's own key, stored encrypted in the shared users table
       (openrouter_key_enc) — this is where the key now lives after being
       moved out of environment configuration into the database.
    2. The app-level OPENROUTER_API_KEY env var, kept only as a legacy fallback.

    Returns None if neither is available.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is not None and user.openrouter_key_enc:
        try:
            from backend.utils.crypto import decrypt_value
            key = decrypt_value(user.openrouter_key_enc)
            if key:
                return key
        except Exception:
            logger.warning('fun_stats: failed to decrypt stored OpenRouter key for user %s', user_id, exc_info=True)
    return OPENROUTER_API_KEY or None


# ---------------------------------------------------------------------------
# OpenRouter call
# ---------------------------------------------------------------------------

def generate_fun_stats(
    data: dict,
    language: str = 'pl',
    api_key: Optional[str] = None,
) -> tuple[list, str]:
    """Generate humorous stats via OpenRouter. Returns (stats_list, model_used).

    ``data`` is the raw flight data from :func:`collect_raw_flights`; the model
    derives its own stats from it.

    Strategy:
    1. Try the preferred creative model (paid — the user's own key).
    2. On failure, try openrouter/free (meta-model, OR auto-selects a free provider).
    3. On failure, try the explicit free model list with OR's route:fallback.
    Returns ([], '') on total failure.
    """
    key = api_key or OPENROUTER_API_KEY
    if not key:
        logger.warning('fun_stats: no OpenRouter API key available, skipping generation')
        return [], ''

    prompt = build_fun_stats_prompt(data, language)

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

    # Attempt 1: preferred creative model (paid — uses the user's own key)
    try:
        return _call({
            'model':       _PRIMARY_FUN_STATS_MODEL,
            'messages':    [{'role': 'user', 'content': prompt}],
            'temperature': 0.9,
            'max_tokens':  2048,
        })
    except Exception:
        logger.warning('fun_stats: preferred model %s failed, falling back to free models',
                       _PRIMARY_FUN_STATS_MODEL, exc_info=True)

    # Attempt 2: openrouter/free meta-model
    try:
        return _call({
            'model':       'openrouter/free',
            'messages':    [{'role': 'user', 'content': prompt}],
            'temperature': 0.9,
            'max_tokens':  2048,
        })
    except Exception:
        logger.warning('fun_stats: openrouter/free failed, trying explicit model list', exc_info=True)

    # Attempt 3: explicit free model list with OR fallback routing
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
