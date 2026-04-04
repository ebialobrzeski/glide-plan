"""Alerts service — checks flight currency and licence validity."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.flight import Flight
from backend.models.user import User


def get_alerts(db: Session, user: User) -> list[dict]:
    alerts: list[dict] = []
    today = date.today()

    # Last flight overall
    last_overall = _last_flight_date(db, user, launch_type=None)
    if last_overall:
        days = (today - last_overall).days
        if days > 90:
            alerts.append(_alert('danger', 'Brak lotu od ponad 90 dni', days, 'no_flight_90'))
        elif days > 60:
            alerts.append(_alert('warning', 'Brak lotu od ponad 60 dni', days, 'no_flight_60'))
    else:
        alerts.append(_alert('info', 'Brak zarejestrowanych lotów', 0, 'no_flights'))

    # Winch launch currency
    last_w = _last_flight_date(db, user, launch_type='W')
    if last_w:
        days_w = (today - last_w).days
        if days_w > 90:
            alerts.append(_alert('danger', 'Brak startu z wyciągarki od ponad 90 dni', days_w, 'winch_90'))
        elif days_w > 30:
            alerts.append(_alert('warning', 'Brak startu z wyciągarki od ponad 30 dni', days_w, 'winch_30'))
    else:
        alerts.append(_alert('warning', 'Brak zarejestrowanego startu z wyciągarki', 0, 'no_winch'))

    # Aero tow currency
    last_s = _last_flight_date(db, user, launch_type='S')
    if last_s:
        days_s = (today - last_s).days
        if days_s > 180:
            alerts.append(_alert('danger', 'Brak aeroholowania od ponad 180 dni', days_s, 'aerotow_180'))
        elif days_s > 90:
            alerts.append(_alert('warning', 'Brak aeroholowania od ponad 90 dni', days_s, 'aerotow_90'))

    # Medical expiry
    if user.logbook_medical_expiry:
        days_med = (user.logbook_medical_expiry - today).days
        if days_med < 0:
            alerts.append(_alert('danger', 'Orzeczenie lekarskie wygasło', abs(days_med), 'medical_expired'))
        elif days_med <= 30:
            alerts.append(_alert('warning', f'Orzeczenie lekarskie wygasa za {days_med} dni', days_med, 'medical_soon'))

    return alerts


def _last_flight_date(db: Session, user: User, launch_type: Optional[str]) -> Optional[date]:
    q = db.query(func.max(Flight.date)).filter(Flight.user_id == user.id)
    if launch_type:
        q = q.filter(Flight.launch_type == launch_type)
    result = q.scalar()
    return result


def _alert(level: str, message: str, days_since: int, code: str) -> dict:
    return {'level': level, 'message': message, 'days_since': days_since, 'code': code}
