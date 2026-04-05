"""Stats service — aggregate flight statistics for GlideLog."""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import extract, func, literal_column
from sqlalchemy.orm import Session

from backend.models.flight import Flight
from backend.models.user import User

# Month abbreviations (English).  Polish labels are applied via i18n in templates.
_MONTH_SHORT = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def _normalize_launch_type(lt: Optional[str]) -> str:
    """Normalize launch_type to a canonical code.

    Handles formats like 'S 800' (aerotow to 800 m) -> 'S'.
    """
    if not lt:
        return 'other'
    lt = lt.strip()
    if lt.upper().startswith('S'):
        return 'S'
    if lt.upper() == 'W':
        return 'W'
    if lt.upper() == 'E':
        return 'E'
    return 'other'


# ---------------------------------------------------------------------------
# Top-level summary
# ---------------------------------------------------------------------------

def summary(db: Session, user: User) -> dict:
    """Return overall lifetime stats for a user."""
    row = db.query(
        func.count(Flight.id).label('total_flights'),
        func.coalesce(func.sum(Flight.flight_time_min), 0).label('total_minutes'),
        func.coalesce(func.sum(Flight.price), 0).label('total_cost'),
        func.max(Flight.date).label('last_flight_date'),
        func.min(Flight.date).label('first_flight_date'),
        func.avg(Flight.flight_time_min).label('avg_flight_min'),
        func.max(Flight.flight_time_min).label('max_flight_min'),
    ).filter(Flight.user_id == user.id).one()

    total_flights = row.total_flights or 0
    total_minutes = int(row.total_minutes or 0)
    avg_min = float(row.avg_flight_min or 0)
    max_min = int(row.max_flight_min or 0)

    h, m = divmod(total_minutes, 60)
    avg_h, avg_m = divmod(int(avg_min), 60)
    max_h, max_m = divmod(max_min, 60)

    # Flying days (distinct dates with at least one flight)
    flying_days = db.query(
        func.count(func.distinct(Flight.date))
    ).filter(Flight.user_id == user.id).scalar() or 0

    # Distinct aircraft (type + reg combinations)
    aircraft_count = db.query(
        func.count(func.distinct(Flight.aircraft_reg))
    ).filter(
        Flight.user_id == user.id,
        Flight.aircraft_reg.isnot(None),
    ).scalar() or 0

    # Distinct aircraft types
    aircraft_types = db.query(
        func.count(func.distinct(Flight.aircraft_type))
    ).filter(
        Flight.user_id == user.id,
        Flight.aircraft_type.isnot(None),
    ).scalar() or 0

    return {
        'total_flights':          total_flights,
        'total_flight_time_min':  total_minutes,
        'total_flight_time_str':  f'{h}h {m:02d}m',
        'total_cost':             float(row.total_cost or 0),
        'last_flight_date':       row.last_flight_date.isoformat() if row.last_flight_date else None,
        'first_flight_date':      row.first_flight_date.isoformat() if row.first_flight_date else None,
        'avg_flight_min':         int(avg_min),
        'avg_flight_str':         f'{avg_h}h {avg_m:02d}m' if total_flights else '—',
        'max_flight_min':         max_min,
        'max_flight_str':         f'{max_h}h {max_m:02d}m' if total_flights else '—',
        'flying_days':            flying_days,
        'aircraft_count':         aircraft_count,
        'aircraft_types':         aircraft_types,
    }


# ---------------------------------------------------------------------------
# Season-filtered summary
# ---------------------------------------------------------------------------

def summary_season(db: Session, user: User, year: int,
                   month_start: int = 4, month_end: int = 10) -> dict:
    """Stats for a single soaring season (default April–October)."""
    season_start = date(year, month_start, 1)
    season_end   = date(year, month_end, calendar.monthrange(year, month_end)[1])

    q = db.query(
        func.count(Flight.id).label('total_flights'),
        func.coalesce(func.sum(Flight.flight_time_min), 0).label('total_minutes'),
        func.coalesce(func.sum(Flight.price), 0).label('total_cost'),
        func.max(Flight.date).label('last_flight_date'),
        func.avg(Flight.flight_time_min).label('avg_flight_min'),
        func.max(Flight.flight_time_min).label('max_flight_min'),
    ).filter(
        Flight.user_id == user.id,
        Flight.date >= season_start,
        Flight.date <= season_end,
    ).one()

    total_minutes = int(q.total_minutes or 0)
    avg_min = float(q.avg_flight_min or 0)
    max_min = int(q.max_flight_min or 0)
    h, m = divmod(total_minutes, 60)
    avg_h, avg_m = divmod(int(avg_min), 60)
    max_h, max_m = divmod(max_min, 60)
    total_flights = q.total_flights or 0

    flying_days = db.query(
        func.count(func.distinct(Flight.date))
    ).filter(
        Flight.user_id == user.id,
        Flight.date >= season_start,
        Flight.date <= season_end,
    ).scalar() or 0

    aircraft_count = db.query(
        func.count(func.distinct(Flight.aircraft_reg))
    ).filter(
        Flight.user_id == user.id,
        Flight.date >= season_start,
        Flight.date <= season_end,
        Flight.aircraft_reg.isnot(None),
    ).scalar() or 0

    aircraft_types = db.query(
        func.count(func.distinct(Flight.aircraft_type))
    ).filter(
        Flight.user_id == user.id,
        Flight.date >= season_start,
        Flight.date <= season_end,
        Flight.aircraft_type.isnot(None),
    ).scalar() or 0

    return {
        'year':                   year,
        'season_label':           f'{year}',
        'total_flights':          total_flights,
        'total_flight_time_min':  total_minutes,
        'total_flight_time_str':  f'{h}h {m:02d}m',
        'total_cost':             float(q.total_cost or 0),
        'last_flight_date':       q.last_flight_date.isoformat() if q.last_flight_date else None,
        'avg_flight_min':         int(avg_min),
        'avg_flight_str':         f'{avg_h}h {avg_m:02d}m' if total_flights else '—',
        'max_flight_min':         max_min,
        'max_flight_str':         f'{max_h}h {max_m:02d}m' if total_flights else '—',
        'flying_days':            flying_days,
        'aircraft_count':         aircraft_count,
        'aircraft_types':         aircraft_types,
    }


# ---------------------------------------------------------------------------
# Range-based summary (arbitrary date_from / date_to)
# ---------------------------------------------------------------------------

def summary_range(db: Session, user: User,
                  date_from: date, date_to: date) -> dict:
    """Return stats for an arbitrary date range."""
    q = db.query(
        func.count(Flight.id).label('total_flights'),
        func.coalesce(func.sum(Flight.flight_time_min), 0).label('total_minutes'),
        func.coalesce(func.sum(Flight.price), 0).label('total_cost'),
        func.max(Flight.date).label('last_flight_date'),
        func.avg(Flight.flight_time_min).label('avg_flight_min'),
        func.max(Flight.flight_time_min).label('max_flight_min'),
    ).filter(
        Flight.user_id == user.id,
        Flight.date >= date_from,
        Flight.date <= date_to,
    ).one()

    total_minutes = int(q.total_minutes or 0)
    avg_min = float(q.avg_flight_min or 0)
    max_min = int(q.max_flight_min or 0)
    h, m = divmod(total_minutes, 60)
    avg_h, avg_m = divmod(int(avg_min), 60)
    max_h, max_m = divmod(max_min, 60)
    total_flights = q.total_flights or 0

    flying_days = db.query(
        func.count(func.distinct(Flight.date))
    ).filter(
        Flight.user_id == user.id,
        Flight.date >= date_from,
        Flight.date <= date_to,
    ).scalar() or 0

    aircraft_count = db.query(
        func.count(func.distinct(Flight.aircraft_reg))
    ).filter(
        Flight.user_id == user.id,
        Flight.date >= date_from,
        Flight.date <= date_to,
        Flight.aircraft_reg.isnot(None),
    ).scalar() or 0

    aircraft_types = db.query(
        func.count(func.distinct(Flight.aircraft_type))
    ).filter(
        Flight.user_id == user.id,
        Flight.date >= date_from,
        Flight.date <= date_to,
        Flight.aircraft_type.isnot(None),
    ).scalar() or 0

    return {
        'date_from':              date_from.isoformat(),
        'date_to':                date_to.isoformat(),
        'total_flights':          total_flights,
        'total_flight_time_min':  total_minutes,
        'total_flight_time_str':  f'{h}h {m:02d}m',
        'total_cost':             float(q.total_cost or 0),
        'last_flight_date':       q.last_flight_date.isoformat() if q.last_flight_date else None,
        'avg_flight_min':         int(avg_min),
        'avg_flight_str':         f'{avg_h}h {avg_m:02d}m' if total_flights else '—',
        'max_flight_min':         max_min,
        'max_flight_str':         f'{max_h}h {max_m:02d}m' if total_flights else '—',
        'flying_days':            flying_days,
        'aircraft_count':         aircraft_count,
        'aircraft_types':         aircraft_types,
    }


# ---------------------------------------------------------------------------
# Monthly breakdown
# ---------------------------------------------------------------------------

def by_month(db: Session, user: User,
             date_from: Optional[date] = None,
             date_to: Optional[date] = None) -> list[dict]:
    """Monthly totals, optionally restricted to a date range."""
    q = db.query(
        extract('year',  Flight.date).label('year'),
        extract('month', Flight.date).label('month'),
        func.count(Flight.id).label('flights'),
        func.coalesce(func.sum(Flight.flight_time_min), 0).label('minutes'),
        func.coalesce(func.sum(Flight.price), 0).label('cost'),
    ).filter(
        Flight.user_id == user.id,
        Flight.date.isnot(None),
    )

    if date_from:
        q = q.filter(Flight.date >= date_from)
    if date_to:
        q = q.filter(Flight.date <= date_to)

    rows = q.group_by('year', 'month').order_by('year', 'month').all()

    return [
        {
            'year':    int(r.year),
            'month':   int(r.month),
            'label':   _MONTH_SHORT[int(r.month)],
            'flights': r.flights,
            'minutes': int(r.minutes),
            'cost':    float(r.cost),
        }
        for r in rows
    ]


def by_month_and_launch(db: Session, user: User,
                        date_from: Optional[date] = None,
                        date_to: Optional[date] = None) -> list[dict]:
    """Monthly totals broken down by launch type — used for stacked bar charts."""
    q = db.query(
        extract('year',  Flight.date).label('year'),
        extract('month', Flight.date).label('month'),
        Flight.launch_type,
        func.count(Flight.id).label('flights'),
        func.coalesce(func.sum(Flight.flight_time_min), 0).label('minutes'),
    ).filter(
        Flight.user_id == user.id,
        Flight.date.isnot(None),
    )

    if date_from:
        q = q.filter(Flight.date >= date_from)
    if date_to:
        q = q.filter(Flight.date <= date_to)

    rows = q.group_by('year', 'month', Flight.launch_type).order_by('year', 'month').all()

    # Normalize launch_type (e.g. 'S 800' -> 'S') and aggregate duplicates
    agg: dict = {}
    for r in rows:
        lt = _normalize_launch_type(r.launch_type)
        key = (int(r.year), int(r.month), lt)
        if key not in agg:
            agg[key] = {
                'year':        int(r.year),
                'month':       int(r.month),
                'label':       _MONTH_SHORT[int(r.month)],
                'launch_type': lt,
                'flights':     0,
                'minutes':     0,
            }
        agg[key]['flights'] += r.flights
        agg[key]['minutes'] += int(r.minutes)

    return sorted(agg.values(), key=lambda x: (x['year'], x['month']))


# ---------------------------------------------------------------------------
# Aircraft breakdown
# ---------------------------------------------------------------------------

def by_aircraft(db: Session, user: User,
                date_from: Optional[date] = None,
                date_to: Optional[date] = None) -> list[dict]:
    q = db.query(
        Flight.aircraft_type,
        Flight.aircraft_reg,
        func.count(Flight.id).label('flights'),
        func.coalesce(func.sum(Flight.flight_time_min), 0).label('minutes'),
    ).filter(Flight.user_id == user.id)

    if date_from:
        q = q.filter(Flight.date >= date_from)
    if date_to:
        q = q.filter(Flight.date <= date_to)

    rows = q.group_by(Flight.aircraft_type, Flight.aircraft_reg).order_by(func.count(Flight.id).desc()).all()

    return [
        {
            'aircraft_type': r.aircraft_type,
            'aircraft_reg':  r.aircraft_reg,
            'flights':       r.flights,
            'minutes':       int(r.minutes),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Launch type breakdown
# ---------------------------------------------------------------------------

def by_launch_type(db: Session, user: User,
                   date_from: Optional[date] = None,
                   date_to: Optional[date] = None) -> list[dict]:
    q = db.query(
        Flight.launch_type,
        func.count(Flight.id).label('flights'),
        func.coalesce(func.sum(Flight.flight_time_min), 0).label('minutes'),
    ).filter(Flight.user_id == user.id)

    if date_from:
        q = q.filter(Flight.date >= date_from)
    if date_to:
        q = q.filter(Flight.date <= date_to)

    rows = q.group_by(Flight.launch_type).order_by(func.count(Flight.id).desc()).all()

    # Normalize and aggregate (e.g. 'S 800' and 'S 1000' both become 'S')
    agg: dict = {}
    for r in rows:
        lt = _normalize_launch_type(r.launch_type)
        if lt not in agg:
            agg[lt] = {'launch_type': lt, 'flights': 0, 'minutes': 0}
        agg[lt]['flights'] += r.flights
        agg[lt]['minutes'] += int(r.minutes)

    return sorted(agg.values(), key=lambda x: -x['flights'])


# ---------------------------------------------------------------------------
# Task breakdown
# ---------------------------------------------------------------------------

def by_task(db: Session, user: User,
            date_from: Optional[date] = None,
            date_to: Optional[date] = None) -> list[dict]:
    q = db.query(
        Flight.task,
        func.count(Flight.id).label('flights'),
        func.coalesce(func.sum(Flight.flight_time_min), 0).label('minutes'),
    ).filter(Flight.user_id == user.id, Flight.task.isnot(None))

    if date_from:
        q = q.filter(Flight.date >= date_from)
    if date_to:
        q = q.filter(Flight.date <= date_to)

    rows = q.group_by(Flight.task).order_by(func.count(Flight.id).desc()).all()
    return [{'task': r.task, 'flights': r.flights, 'minutes': int(r.minutes)} for r in rows]


# ---------------------------------------------------------------------------
# Instructors breakdown
# ---------------------------------------------------------------------------

def by_instructor(db: Session, user: User,
                  date_from: Optional[date] = None,
                  date_to: Optional[date] = None) -> list[dict]:
    """Returns instructors the user has flown with, ranked by number of flights."""
    q = db.query(
        Flight.instructor,
        func.count(Flight.id).label('flights'),
        func.coalesce(func.sum(Flight.flight_time_min), 0).label('minutes'),
    ).filter(
        Flight.user_id == user.id,
        Flight.instructor.isnot(None),
        Flight.instructor != '',
    )

    if date_from:
        q = q.filter(Flight.date >= date_from)
    if date_to:
        q = q.filter(Flight.date <= date_to)

    rows = q.group_by(Flight.instructor).order_by(func.count(Flight.id).desc()).all()
    return [{'instructor': r.instructor, 'flights': r.flights, 'minutes': int(r.minutes)} for r in rows]


# ---------------------------------------------------------------------------
# Winch operators (from raw_data JSON)
# ---------------------------------------------------------------------------

def by_winch_operator(db: Session, user: User,
                      date_from: Optional[date] = None,
                      date_to: Optional[date] = None) -> list[dict]:
    """Rank winch operators from the crew.winch_operator field in raw_data."""
    from sqlalchemy import cast, type_coerce
    from sqlalchemy.dialects.postgresql import JSONB

    q = db.query(
        Flight.raw_data['crew']['winch_operator'].astext.label('operator'),
        func.count(Flight.id).label('launches'),
    ).filter(
        Flight.user_id == user.id,
        Flight.launch_type == 'W',
        Flight.raw_data['crew']['winch_operator'].astext.isnot(None),
    )

    if date_from:
        q = q.filter(Flight.date >= date_from)
    if date_to:
        q = q.filter(Flight.date <= date_to)

    rows = q.group_by('operator').order_by(func.count(Flight.id).desc()).all()
    return [{'operator': r.operator, 'launches': r.launches} for r in rows]


# ---------------------------------------------------------------------------
# Longest flights
# ---------------------------------------------------------------------------

def longest_flights(db: Session, user: User, limit: int = 5,
                    date_from: Optional[date] = None,
                    date_to: Optional[date] = None) -> list[dict]:
    q = db.query(Flight).filter(
        Flight.user_id == user.id,
        Flight.flight_time_min.isnot(None),
    )

    if date_from:
        q = q.filter(Flight.date >= date_from)
    if date_to:
        q = q.filter(Flight.date <= date_to)

    rows = q.order_by(Flight.flight_time_min.desc()).limit(limit).all()
    return [
        {
            'date':          r.date.isoformat() if r.date else None,
            'aircraft_type': r.aircraft_type,
            'aircraft_reg':  r.aircraft_reg,
            'flight_time_min': r.flight_time_min,
            'task':          r.task,
            'h':             r.flight_time_min // 60 if r.flight_time_min else 0,
            'm':             r.flight_time_min % 60  if r.flight_time_min else 0,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Currency helpers (used by alerts + licenses page)
# ---------------------------------------------------------------------------

def last_flight_by_launch(db: Session, user: User,
                          launch_type: Optional[str] = None) -> Optional[date]:
    """Return the date of the most recent flight, optionally filtered by launch type."""
    q = db.query(func.max(Flight.date)).filter(Flight.user_id == user.id)
    if launch_type:
        q = q.filter(Flight.launch_type == launch_type)
    return q.scalar()


def flights_in_window(db: Session, user: User,
                      window_days: int = 730,
                      launch_type: Optional[str] = None) -> dict:
    """Count flights and total minutes in the last N days.

    Used for EASA SFCL.160 biennual currency checks (default 24 months = 730 days).
    """
    cutoff = date.today() - timedelta(days=window_days)
    q = db.query(
        func.count(Flight.id).label('flights'),
        func.coalesce(func.sum(Flight.flight_time_min), 0).label('minutes'),
    ).filter(
        Flight.user_id == user.id,
        Flight.date >= cutoff,
    )
    if launch_type:
        q = q.filter(Flight.launch_type == launch_type)

    row = q.one()
    h, m = divmod(int(row.minutes), 60)
    return {
        'flights': row.flights,
        'minutes': int(row.minutes),
        'flight_time_str': f'{h}h {m:02d}m',
        'window_days': window_days,
        'cutoff': cutoff.isoformat(),
    }


def pic_totals(db: Session, user: User) -> dict:
    """Total PIC flights and minutes (is_instructor=False, or all if not tracked)."""
    row = db.query(
        func.count(Flight.id).label('flights'),
        func.coalesce(func.sum(Flight.flight_time_min), 0).label('minutes'),
    ).filter(
        Flight.user_id == user.id,
        Flight.is_instructor.is_(False),
    ).one()

    h, m = divmod(int(row.minutes), 60)
    return {
        'flights': row.flights,
        'minutes': int(row.minutes),
        'flight_time_str': f'{h}h {m:02d}m',
    }


# ---------------------------------------------------------------------------
# Weekly activity grid
# ---------------------------------------------------------------------------

def weekly_activity(db: Session, user: User, weeks: int = 26) -> list[dict]:
    """Return per-day flight counts for the last N weeks — used for activity heat-map."""
    cutoff = date.today() - timedelta(weeks=weeks)
    rows = db.query(
        Flight.date,
        func.count(Flight.id).label('flights'),
    ).filter(
        Flight.user_id == user.id,
        Flight.date >= cutoff,
    ).group_by(Flight.date).order_by(Flight.date).all()

    return [{'date': r.date.isoformat(), 'flights': r.flights} for r in rows]


# ---------------------------------------------------------------------------
# Fun facts / ciekawostki
# ---------------------------------------------------------------------------

def fun_facts(db: Session, user: User,
              date_from: Optional[date] = None,
              date_to: Optional[date] = None) -> dict:
    """Compute miscellaneous fun statistics for the statistics page."""
    q_base = db.query(Flight).filter(Flight.user_id == user.id)
    if date_from:
        q_base = q_base.filter(Flight.date >= date_from)
    if date_to:
        q_base = q_base.filter(Flight.date <= date_to)

    # Most active day
    most_active_row = db.query(
        Flight.date,
        func.count(Flight.id).label('flights'),
    ).filter(
        Flight.user_id == user.id,
        *([Flight.date >= date_from] if date_from else []),
        *([Flight.date <= date_to] if date_to else []),
    ).group_by(Flight.date).order_by(func.count(Flight.id).desc()).first()

    # Favourite takeoff hour
    fav_hour_row = db.query(
        extract('hour', Flight.takeoff_time).label('hour'),
        func.count(Flight.id).label('cnt'),
    ).filter(
        Flight.user_id == user.id,
        Flight.takeoff_time.isnot(None),
        *([Flight.date >= date_from] if date_from else []),
        *([Flight.date <= date_to] if date_to else []),
    ).group_by('hour').order_by(func.count(Flight.id).desc()).first()

    # Estimated distance (rough: avg glide ratio 30 * minutes * (km/min at 100km/h))
    total_minutes_row = db.query(
        func.coalesce(func.sum(Flight.flight_time_min), 0)
    ).filter(
        Flight.user_id == user.id,
        *([Flight.date >= date_from] if date_from else []),
        *([Flight.date <= date_to] if date_to else []),
    ).scalar() or 0
    # Estimated at 100 km/h average cross-country speed
    estimated_km = round(int(total_minutes_row) / 60 * 100)

    # First task (S500, FAI triangle, etc.)
    first_task_row = db.query(Flight).filter(
        Flight.user_id == user.id,
        Flight.task.isnot(None),
        Flight.task != '',
        *([Flight.date >= date_from] if date_from else []),
        *([Flight.date <= date_to] if date_to else []),
    ).order_by(Flight.date.asc()).first()

    return {
        'estimated_km':      estimated_km,
        'most_active_date':  most_active_row.date.isoformat() if most_active_row else None,
        'most_active_count': most_active_row.flights if most_active_row else 0,
        'favourite_hour':    f'{int(fav_hour_row.hour):02d}:00' if fav_hour_row else None,
        'first_task':        first_task_row.task if first_task_row else None,
        'first_task_date':   first_task_row.date.isoformat() if first_task_row else None,
    }
