"""Stats service — aggregate flight statistics."""
from __future__ import annotations

from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from backend.models.flight import Flight
from backend.models.user import User


def summary(db: Session, user: User) -> dict:
    row = db.query(
        func.count(Flight.id).label('total_flights'),
        func.coalesce(func.sum(Flight.flight_time_min), 0).label('total_minutes'),
        func.coalesce(func.sum(Flight.price), 0).label('total_cost'),
        func.max(Flight.date).label('last_flight_date'),
    ).filter(Flight.user_id == user.id).one()

    h, m = divmod(int(row.total_minutes), 60)
    return {
        'total_flights': row.total_flights,
        'total_flight_time_min': int(row.total_minutes),
        'total_flight_time_str': f'{h}h {m:02d}m',
        'total_cost': float(row.total_cost),
        'last_flight_date': row.last_flight_date.isoformat() if row.last_flight_date else None,
    }


def by_month(db: Session, user: User) -> list[dict]:
    rows = (
        db.query(
            extract('year', Flight.date).label('year'),
            extract('month', Flight.date).label('month'),
            func.count(Flight.id).label('flights'),
            func.coalesce(func.sum(Flight.flight_time_min), 0).label('minutes'),
        )
        .filter(Flight.user_id == user.id)
        .group_by('year', 'month')
        .order_by('year', 'month')
        .all()
    )
    return [
        {
            'year': int(r.year),
            'month': int(r.month),
            'label': f'{int(r.year)}-{int(r.month):02d}',
            'flights': r.flights,
            'minutes': int(r.minutes),
        }
        for r in rows
    ]


def by_aircraft(db: Session, user: User) -> list[dict]:
    rows = (
        db.query(
            Flight.aircraft_type,
            Flight.aircraft_reg,
            func.count(Flight.id).label('flights'),
            func.coalesce(func.sum(Flight.flight_time_min), 0).label('minutes'),
        )
        .filter(Flight.user_id == user.id)
        .group_by(Flight.aircraft_type, Flight.aircraft_reg)
        .order_by(func.count(Flight.id).desc())
        .all()
    )
    return [
        {
            'aircraft_type': r.aircraft_type,
            'aircraft_reg': r.aircraft_reg,
            'flights': r.flights,
            'minutes': int(r.minutes),
        }
        for r in rows
    ]


def by_launch_type(db: Session, user: User) -> list[dict]:
    rows = (
        db.query(
            Flight.launch_type,
            func.count(Flight.id).label('flights'),
            func.coalesce(func.sum(Flight.flight_time_min), 0).label('minutes'),
        )
        .filter(Flight.user_id == user.id)
        .group_by(Flight.launch_type)
        .order_by(func.count(Flight.id).desc())
        .all()
    )
    return [{'launch_type': r.launch_type, 'flights': r.flights, 'minutes': int(r.minutes)} for r in rows]


def by_task(db: Session, user: User) -> list[dict]:
    rows = (
        db.query(
            Flight.task,
            func.count(Flight.id).label('flights'),
        )
        .filter(Flight.user_id == user.id)
        .group_by(Flight.task)
        .order_by(func.count(Flight.id).desc())
        .all()
    )
    return [{'task': r.task, 'flights': r.flights} for r in rows]
