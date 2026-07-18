"""GlideLog — fun stats API endpoints."""
from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone

from flask import jsonify
from flask_login import current_user

from backend.db import get_db, get_engine
from backend.models.fun_stats_cache import FunStatsCache
from backend.routes.logbook import logbook_bp
from backend.services.logbook import fun_stats as fun_stats_svc
from backend.utils.auth_decorators import login_required

logger = logging.getLogger(__name__)
_CACHE_TTL_HOURS = 24
_ERROR_SENTINEL = 'error'


@logbook_bp.route('/api/stats/fun', methods=['GET'])
@login_required
def fun_stats_get():
    """Return cached fun stats if fresh (< 24h), otherwise 202 + generating flag."""
    db = get_db()
    cache = db.query(FunStatsCache).filter_by(user_id=current_user.id).first()
    if cache:
        age = datetime.now(timezone.utc) - cache.generated_at
        if age < timedelta(hours=_CACHE_TTL_HOURS):
            # Error state: generation previously failed
            if cache.model_used == _ERROR_SENTINEL:
                return jsonify({'error': True}), 200
            return jsonify({
                'stats':        cache.content,
                'generated_at': cache.generated_at.isoformat(),
                'model_used':   cache.model_used,
                'from_cache':   True,
            })
    return jsonify({'generating': True}), 202


@logbook_bp.route('/api/stats/fun/refresh', methods=['POST'])
@login_required
def fun_stats_refresh():
    """Trigger (re)generation of fun stats; rate-limited to once per 24 h."""
    db = get_db()
    cache = db.query(FunStatsCache).filter_by(user_id=current_user.id).first()
    if cache:
        age = datetime.now(timezone.utc) - cache.generated_at
        # Don't rate-limit if the previous attempt errored out
        if age < timedelta(hours=_CACHE_TTL_HOURS) and cache.model_used != _ERROR_SENTINEL:
            seconds_left = _CACHE_TTL_HOURS * 3600 - age.total_seconds()
            hours_left   = int(seconds_left // 3600)
            minutes_left = int((seconds_left % 3600) // 60)
            next_at = (cache.generated_at + timedelta(hours=_CACHE_TTL_HOURS)).isoformat()
            return jsonify({
                'error':          'too_soon',
                'message':        f'Możesz wygenerować ponownie za {hours_left}h {minutes_left}min',
                'next_available': next_at,
            }), 429

    language = current_user.preferred_language or 'pl'
    user_id  = current_user.id
    threading.Thread(
        target=_generate_and_cache,
        args=(user_id, language),
        daemon=True,
    ).start()
    return jsonify({'message': 'generating'})


def _generate_and_cache(user_id: uuid.UUID, language: str = 'pl') -> None:
    """Background worker: collect stats, call LLM, persist cache.

    Always writes a result to fun_stats_cache — either the generated stats
    or an error sentinel — so the frontend’s polling loop always terminates.
    """
    from sqlalchemy.orm import sessionmaker  # local import to avoid circulars

    engine = get_engine()
    if engine is None:
        logger.error('fun_stats: DB engine not available, aborting generation for user %s', user_id)
        return

    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()
    try:
        logger.info('fun_stats: starting generation for user %s (lang=%s)', user_id, language)
        stats = fun_stats_svc.collect_pilot_stats(db, user_id)
        logger.info('fun_stats: collected pilot stats for user %s: %d flights', user_id, stats.get('total_flights', 0))
        result, model = fun_stats_svc.generate_fun_stats(stats, language)
        if result:
            fun_stats_svc.upsert_cache(db, user_id, result, model)
            logger.info('fun_stats: cached %d stats via model %s for user %s', len(result), model, user_id)
        else:
            # All LLM models failed — write error sentinel so polling stops
            logger.error('fun_stats: all models failed for user %s, writing error sentinel', user_id)
            fun_stats_svc.upsert_cache(db, user_id, [], _ERROR_SENTINEL)
    except Exception:
        logger.exception('fun_stats: background generation failed for user %s', user_id)
        try:
            fun_stats_svc.upsert_cache(db, user_id, [], _ERROR_SENTINEL)
        except Exception:
            logger.exception('fun_stats: could not write error sentinel for user %s', user_id)
    finally:
        db.close()
