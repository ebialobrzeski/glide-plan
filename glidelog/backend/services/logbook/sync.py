"""Sync service — runs a connector and persists new flights."""
from __future__ import annotations

import logging
import threading
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text, update as sa_update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.models.connector import Connector
from backend.models.flight import Flight
from backend.models.sync_log import SyncLog
from backend.services.connectors import get_connector

logger = logging.getLogger(__name__)

# Days to look back BEFORE the most recent stored flight when syncing.
# Flights are often entered several days late, so a backdated flight can land
# earlier than one we already have. Re-scanning this buffer each sync catches
# them; ON CONFLICT keeps the overlap idempotent.
_BACKFILL_BUFFER_DAYS = 14


def sync_connector(db: Session, connector: Connector) -> SyncLog:
    """
    Synchronise flights for one connector.
    Handles its own commit/rollback — callers must NOT call db.commit() afterwards.
    Returns a SyncLog with the final status.
    """
    started_at = datetime.now(timezone.utc)
    connector_id = connector.id
    user_id = connector.user_id
    imported = 0

    try:
        # Determine the fetch window.
        #
        # We anchor date_from to the date of the most recent flight already
        # stored for this connector — NOT to the last sync time — minus a
        # buffer. Flights are frequently entered a few days after the flight
        # itself, so a backdated flight can appear in the source only after a
        # sync and even predate the newest flight we already hold. Re-fetching
        # from (latest flight date - buffer) each time catches those late
        # entries; ON CONFLICT (user_id, external_id) keeps the overlapping
        # re-fetch idempotent (no duplicates).
        latest_flight_date = (
            db.query(Flight.date)
            .filter(
                Flight.connector_id == connector_id,
                Flight.date.isnot(None),
            )
            .order_by(Flight.date.desc())
            .limit(1)
            .scalar()
        )
        if latest_flight_date:
            date_from = latest_flight_date - timedelta(days=_BACKFILL_BUFFER_DAYS)
        else:
            date_from = date(2000, 1, 1)

        impl = get_connector(connector)
        raw_flights = impl.fetch_flights(date_from, date.today())

        for raw in raw_flights:
            flight_row = _build_flight_row(raw, connector)
            stmt = (
                insert(Flight)
                .values(**flight_row)
                .on_conflict_do_update(
                    index_elements=['user_id', 'external_id'],
                    set_={
                        'aircraft_type': flight_row['aircraft_type'],
                        'aircraft_reg':  flight_row['aircraft_reg'],
                    },
                )
                # xmax = 0 on the returned row means it was INSERTed rather than
                # UPDATEd. Since we now re-fetch an overlapping date window every
                # sync, most rows are UPDATEs — count only genuine inserts so the
                # "imported" total and the fun-stats regen trigger stay accurate.
                .returning(text('(xmax = 0) AS inserted'))
            )
            result = db.execute(stmt)
            row = result.first()
            # Access positionally: this is an ORM insert() executed through a
            # Session, and the anonymous text() column is NOT exposed as a Row
            # attribute — `row.inserted` raises AttributeError('inserted'), which
            # previously aborted the whole sync and rolled back every insert.
            if row is not None and row[0]:
                imported += 1

        finished_at = datetime.now(timezone.utc)
        msg = f'Imported {imported} new flights.'

        # Record success
        log = SyncLog(
            user_id=user_id,
            connector_id=connector_id,
            started_at=started_at,
            finished_at=finished_at,
            status='success',
            message=msg,
            flights_imported=imported,
        )
        db.add(log)
        db.execute(
            sa_update(Connector)
            .where(Connector.id == connector_id)
            .values(
                last_sync_at=finished_at,
                last_sync_status='success',
                updated_at=finished_at,
            )
        )
        db.commit()
        logger.info('Sync success for connector %s: %s', connector_id, msg)

        # Auto-regenerate fun stats if new flights arrived
        if imported > 0:
            _trigger_fun_stats_regen(user_id, connector)

        return log

    except Exception as exc:
        error_msg = str(exc)[:2000]
        finished_at = datetime.now(timezone.utc)
        logger.exception('Sync failed for connector %s', connector_id)

        # Rollback any aborted/partial transaction first
        try:
            db.rollback()
        except Exception:
            pass

        # Persist the error state in a fresh transaction
        try:
            error_log = SyncLog(
                user_id=user_id,
                connector_id=connector_id,
                started_at=started_at,
                finished_at=finished_at,
                status='error',
                message=error_msg,
                flights_imported=imported,
            )
            db.add(error_log)
            db.execute(
                sa_update(Connector)
                .where(Connector.id == connector_id)
                .values(
                    last_sync_status='error',
                    last_sync_at=finished_at,
                )
            )
            db.commit()
            return error_log
        except Exception:
            logger.exception(
                'Failed to save error state for connector %s — giving up', connector_id
            )
            try:
                db.rollback()
            except Exception:
                pass
            stub = SyncLog(status='error', message=error_msg, flights_imported=0)
            return stub


def sync_all_users(db: Session) -> None:
    """Background job: sync all active connectors."""
    connectors = db.query(Connector).filter(Connector.is_active.is_(True)).all()
    for connector in connectors:
        try:
            sync_connector(db, connector)  # commits internally
        except Exception:
            logger.exception('Background sync failed for connector %s', connector.id)


def _trigger_fun_stats_regen(user_id, connector: Connector) -> None:
    """Fire-and-forget: regenerate fun stats for the user in a background thread."""
    from backend.db import get_db as _get_db
    from backend.models.user import User
    from backend.services.logbook import fun_stats as fun_stats_svc

    def _worker():
        db = _get_db()
        try:
            user = db.query(User).get(user_id)
            language = (user.preferred_language if user else None) or 'pl'
            data = fun_stats_svc.collect_raw_flights(db, user_id)
            api_key = fun_stats_svc.resolve_api_key(db, user_id)
            result, model = fun_stats_svc.generate_fun_stats(data, language, api_key=api_key)
            if result:
                fun_stats_svc.upsert_cache(db, user_id, result, model)
        except Exception:
            logger.warning('fun_stats auto-regen failed for user %s', user_id, exc_info=True)
        finally:
            db.close()

    threading.Thread(target=_worker, daemon=True).start()


def _build_flight_row(raw: dict, connector: Connector) -> dict:
    from datetime import time as _time
    import re as _re
    import uuid as _uuid

    def to_time(val):
        if not val:
            return None
        try:
            parts = str(val).split(':')
            return _time(int(parts[0]), int(parts[1]))
        except Exception:
            return None

    def to_date(val):
        if not val:
            return None
        try:
            return date.fromisoformat(str(val))
        except Exception:
            return None

    def to_flight_minutes(raw_dict: dict) -> int | None:
        """Resolve flight time in minutes from either flight_time_min (int)
        or flight_time (HH:MM string) — whichever is present."""
        if raw_dict.get('flight_time_min') is not None:
            try:
                return int(raw_dict['flight_time_min'])
            except (TypeError, ValueError):
                pass
        ft = raw_dict.get('flight_time')
        if ft:
            m = _re.match(r'^(\d+):(\d{2})$', str(ft).strip())
            if m:
                return int(m.group(1)) * 60 + int(m.group(2))
        return None

    def split_aircraft(raw_dict: dict) -> tuple:
        """Return (aircraft_type, aircraft_reg).

        Handles both pre-split keys and the combined 'aircraft' field
        returned by the eChronometraż JSON API.
        """
        if 'aircraft_type' in raw_dict or 'aircraft_reg' in raw_dict:
            return raw_dict.get('aircraft_type') or None, raw_dict.get('aircraft_reg') or None
        combined = raw_dict.get('aircraft', '')
        if not combined:
            return None, None
        reg_match = _re.search(r'\b([A-Z]{1,3}-[A-Z0-9]{3,6})\s*$', combined)
        if reg_match:
            return combined[: reg_match.start()].strip() or None, reg_match.group(1)
        parts = combined.rsplit(' ', 1)
        return (parts[0].strip() or None, parts[1].strip() or None) if len(parts) == 2 else (combined or None, None)

    aircraft_type, aircraft_reg = split_aircraft(raw)

    # price: accept float, int, or string representations
    price = None
    raw_price = raw.get('price')
    if raw_price is not None:
        try:
            price = float(raw_price)
        except (TypeError, ValueError):
            pass

    return {
        'id': _uuid.uuid4(),
        'external_id': raw.get('external_id'),
        'user_id': connector.user_id,
        'date': to_date(raw.get('date')) or date.today(),
        'aircraft_type': aircraft_type,
        'aircraft_reg': aircraft_reg,
        'pilot': raw.get('pilot'),
        'instructor': raw.get('instructor'),
        'task': raw.get('task'),
        'launch_type': raw.get('launch_type'),
        'takeoff_airport': raw.get('takeoff_airport'),
        'takeoff_time': to_time(raw.get('takeoff_time')),
        'landing_airport': raw.get('landing_airport'),
        'landing_time': to_time(raw.get('landing_time')),
        'flight_time_min': to_flight_minutes(raw),
        'landings': raw.get('landings', 1),
        'is_instructor': bool(raw.get('is_instructor', False)),
        'price': price,
        'raw_data': raw.get('raw_data', raw),
        'source': 'echrono' if connector.type == 'echrono' else connector.type,
        'connector_id': connector.id,
        'synced_at': datetime.now(timezone.utc),
    }
