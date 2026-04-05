"""Flight service — CRUD and filtering for flights."""
from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.flight import Flight
from backend.models.import_log import ImportLog
from backend.models.user import User


class FlightServiceError(Exception):
    pass


def list_flights(
    db: Session,
    user: User,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    aircraft_type: Optional[str] = None,
    launch_type: Optional[str] = None,
    task: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[Flight], int]:
    """Return (flights, total_count) matching filters."""
    q = db.query(Flight).filter(Flight.user_id == user.id)
    if date_from:
        q = q.filter(Flight.date >= date_from)
    if date_to:
        q = q.filter(Flight.date <= date_to)
    if aircraft_type:
        q = q.filter(Flight.aircraft_type.ilike(f'%{aircraft_type}%'))
    if launch_type:
        q = q.filter(Flight.launch_type == launch_type)
    if task:
        q = q.filter(Flight.task.ilike(f'%{task}%'))

    total = q.count()
    flights = q.order_by(Flight.date.desc(), Flight.takeoff_time.desc()).offset((page - 1) * limit).limit(limit).all()
    return flights, total


def get_flight(db: Session, user: User, flight_id: str) -> Flight:
    flight = db.query(Flight).filter(Flight.id == flight_id, Flight.user_id == user.id).first()
    if not flight:
        raise FlightServiceError('Flight not found.')
    return flight


def create_manual_flight(db: Session, user: User, data: dict) -> Flight:
    _validate_manual(data)
    raw = {**data}
    import_hash = _make_import_hash(str(user.id), data)
    raw['import_hash'] = import_hash

    flight = Flight(
        id=uuid.uuid4(),
        user_id=user.id,
        source='manual',
        raw_data=raw,
        synced_at=datetime.now(timezone.utc),
        **_extract_fields(data),
    )
    db.add(flight)
    db.flush()
    return flight


def update_manual_flight(db: Session, user: User, flight_id: str, data: dict) -> Flight:
    flight = get_flight(db, user, flight_id)
    if flight.source != 'manual':
        raise FlightServiceError('Only manually added flights can be edited.')
    _validate_manual(data)
    for field, val in _extract_fields(data).items():
        setattr(flight, field, val)
    flight.raw_data = {**(flight.raw_data or {}), **data}
    return flight


def delete_flight(db: Session, user: User, flight_id: str) -> None:
    flight = get_flight(db, user, flight_id)
    if flight.source not in ('manual', 'import'):
        raise FlightServiceError('Only manually added or imported flights can be deleted.')
    db.delete(flight)


def _validate_manual(data: dict) -> None:
    if not data.get('date'):
        raise FlightServiceError('Date is required.')
    try:
        d = date.fromisoformat(data['date'])
        if d > date.today():
            raise FlightServiceError('Date cannot be in the future.')
    except ValueError:
        raise FlightServiceError('Invalid date format.')
    if not data.get('launch_type'):
        raise FlightServiceError('Launch type is required.')


def _extract_fields(data: dict) -> dict:
    from datetime import time as _time

    def to_time(val):
        if not val:
            return None
        try:
            parts = str(val).split(':')
            return _time(int(parts[0]), int(parts[1]))
        except Exception:
            return None

    return {
        'date': date.fromisoformat(data['date']) if data.get('date') else None,
        'aircraft_type': data.get('aircraft_type'),
        'aircraft_reg': data.get('aircraft_reg'),
        'pilot': data.get('pilot'),
        'instructor': data.get('instructor'),
        'task': data.get('task'),
        'launch_type': data.get('launch_type'),
        'takeoff_airport': data.get('takeoff_airport'),
        'takeoff_time': to_time(data.get('takeoff_time')),
        'landing_airport': data.get('landing_airport'),
        'landing_time': to_time(data.get('landing_time')),
        'flight_time_min': data.get('flight_time_min'),
        'landings': data.get('landings', 1),
        'is_instructor': bool(data.get('is_instructor', False)),
        'price': data.get('price'),
    }


def _make_import_hash(user_id: str, data: dict) -> str:
    key = f"{user_id}:{data.get('date')}:{data.get('aircraft_reg')}:{data.get('takeoff_time')}"
    return hashlib.sha256(key.encode()).hexdigest()
