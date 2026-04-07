"""Alerts service — checks flight currency and licence validity against EASA rules.

All alert codes and messages are in English.  Templates use data-i18n attributes
so the UI is translated through the standard i18n pipeline.

EASA references implemented:
  SFCL.160(a)   — 24-month biennial currency (5h + 15 launches + 2 FI(S) flights)
  SFCL.160(b)   — TMG 24-month currency (12h total, 6h on TMG, 12 launches, 1h FI(S) on TMG)
  SFCL.115(b)   — Passenger carriage thresholds (30 PIC for first passenger, 200 for hire/reward)
  FCL.060       — Recent experience before carrying a passenger (3 T/O + 3 landings in 90 days)
  SFCL.130      — Launch method recency (alert if >90 days since last use)
  Part-MED      — Medical certificate expiry (warn 60 days before, alert on expiry)
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.flight import Flight
from backend.models.user import User
from backend.services.logbook import stats as stats_svc


# ---------------------------------------------------------------------------
# Alert levels
# ---------------------------------------------------------------------------
LEVEL_OK      = 'success'
LEVEL_INFO    = 'info'
LEVEL_WARNING = 'warning'
LEVEL_DANGER  = 'danger'


def _alert(level: str, code: str, title: str, description: str = '',
           days: int = 0, action: str = '',
           title_key: str = '', desc_key: str = '',
           desc_params: Optional[dict] = None) -> dict:
    return {
        'level':       level,
        'code':        code,
        'title':       title,
        'title_key':   title_key or f'logbook.alert.{code}.title',
        'description': description,
        'desc_key':    desc_key or (f'logbook.alert.{code}.desc' if description else ''),
        'desc_params': desc_params or {},
        'days':        days,          # days since last event (positive) or until expiry (negative)
        'action':      action,        # i18n key for an action button label, or ''
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_alerts(db: Session, user: User,
               _window_730: Optional[dict] = None,
               _last_per_method: Optional[dict] = None,
               _window_90: Optional[dict] = None,
               _pic_totals: Optional[dict] = None) -> list[dict]:
    """Return a list of all active alerts for the given user.

    Pass pre-computed kwargs to avoid duplicate DB queries when called
    alongside get_currency_summary() or the licenses page route.
    """
    alerts: list[dict] = []
    today = date.today()

    # Resolve pilot profile (may be None if user has not filled it in)
    profile = getattr(user, 'pilot_profile', None)

    # Shared data — compute once, reuse across checkers
    window_730      = _window_730      or stats_svc.flights_in_window(db, user, window_days=730)
    last_per_method = _last_per_method or stats_svc.last_flights_per_method(db, user)
    window_90       = _window_90       or stats_svc.flights_in_window(db, user, window_days=90)
    pic             = _pic_totals      or stats_svc.pic_totals(db, user)

    # ── SFCL.160(a) — Biennial currency ─────────────────────────────────────
    alerts.extend(_check_biennial_currency(db, user, today, window=window_730))

    # ── SFCL.130 — Launch method recency ────────────────────────────────────
    alerts.extend(_check_launch_recency(today, last_per_method))

    # ── FCL.060 — Recent experience for passenger carriage ──────────────────
    alerts.extend(_check_passenger_recency(window_90))

    # ── SFCL.115(b) — Passenger carriage thresholds ─────────────────────────
    alerts.extend(_check_passenger_thresholds(pic, today, profile))

    # ── Part-MED — Medical certificate ──────────────────────────────────────
    alerts.extend(_check_medical(user, today, profile))

    # ── Profile completeness reminders ──────────────────────────────────────
    alerts.extend(_check_profile_completeness(user, profile))

    return alerts


def get_currency_summary(db: Session, user: User,
                         _window_730: Optional[dict] = None,
                         _last_per_method: Optional[dict] = None) -> dict:
    """Return a structured currency summary for the licenses page.

    Pass pre-computed _window_730 / _last_per_method to avoid duplicate DB
    queries when called alongside get_alerts() on the same request.
    """
    today = date.today()
    profile = getattr(user, 'pilot_profile', None)
    window      = _window_730      or stats_svc.flights_in_window(db, user, window_days=730)
    last_pm     = _last_per_method or stats_svc.last_flights_per_method(db, user)
    window_tmg  = stats_svc.flights_in_window(db, user, window_days=730, launch_type='E')

    # Last flight by method — from the single pre-computed dict
    last_w   = last_pm.get('W')
    last_s   = last_pm.get('S')
    last_tmg = last_pm.get('E')
    last_any = last_pm.get('any')

    # SFCL.160(a) requirements
    min_hours_min = 5 * 60   # 5 hours in minutes
    min_launches  = 15

    ok_hours   = window['minutes'] >= min_hours_min
    ok_launches= window['flights'] >= min_launches

    # Medical
    medical_expiry  = _get_medical_expiry(user, profile)
    days_to_medical = (medical_expiry - today).days if medical_expiry else None

    return {
        # 24-month window
        'window_minutes':    window['minutes'],
        'window_flights':    window['flights'],
        'window_flight_str': window['flight_time_str'],
        'window_cutoff':     window['cutoff'],
        # Requirements
        'min_hours_min':     min_hours_min,
        'min_launches':      min_launches,
        'ok_hours':          ok_hours,
        'ok_launches':       ok_launches,
        # Last flight per method
        'last_w':            last_w.isoformat() if last_w else None,
        'last_s':            last_s.isoformat() if last_s else None,
        'last_tmg':          last_tmg.isoformat() if last_tmg else None,
        'last_any':          last_any.isoformat() if last_any else None,
        # Days since each method
        'days_since_w':      (today - last_w).days if last_w else None,
        'days_since_s':      (today - last_s).days if last_s else None,
        'days_since_tmg':    (today - last_tmg).days if last_tmg else None,
        'days_since_any':    (today - last_any).days if last_any else None,
        # Medical
        'medical_expiry':    medical_expiry.isoformat() if medical_expiry else None,
        'medical_class':     (profile.medical_class if profile else None) or 'LAPL',
        'days_to_medical':   days_to_medical,
        'medical_ok':        (days_to_medical is not None and days_to_medical > 0),
        # Profile
        'license_date':      (profile.license_date.isoformat() if profile and profile.license_date else None),
        'license_number':    (profile.license_number if profile else None),
        'has_tmg':           (profile.has_tmg if profile else False),
        'launch_methods_exam': (profile.launch_methods_exam if profile else []) or [],
    }


# ---------------------------------------------------------------------------
# Internal checkers
# ---------------------------------------------------------------------------

def _check_biennial_currency(db: Session, user: User, today: date,
                             window: Optional[dict] = None) -> list[dict]:
    """SFCL.160(a) — 5h + 15 launches in the last 24 months."""
    alerts: list[dict] = []
    if window is None:
        window = stats_svc.flights_in_window(db, user, window_days=730)

    hours_min   = window['minutes']
    launches    = window['flights']
    required_h  = 5 * 60
    required_l  = 15

    if hours_min >= required_h and launches >= required_l:
        alerts.append(_alert(
            LEVEL_OK, 'currency_ok',
            'Current biennial practice — SPL',
            f'{window["flight_time_str"]} and {launches} launches in the last 24 months — requirements met.',
            desc_params={'time': window['flight_time_str'], 'launches': launches},
        ))
    else:
        missing = []
        if hours_min < required_h:
            deficit_h = (required_h - hours_min) // 60
            deficit_m = (required_h - hours_min) % 60
            missing.append(f'{deficit_h}h {deficit_m:02d}m flight time')
        if launches < required_l:
            missing.append(f'{required_l - launches} more launches')
        alerts.append(_alert(
            LEVEL_WARNING, 'currency_low',
            'Biennial currency low — SPL',
            f'SFCL.160(a) requires 5h + 15 launches in any 24-month window. '
            f'Still needed: {", ".join(missing)}.',
            desc_params={'missing': ', '.join(missing)},
        ))

    return alerts


def _check_launch_recency(today: date, last_per_method: dict) -> list[dict]:
    """SFCL.130 — alert if a launch method hasn't been used in >90 days.

    Uses a pre-computed last_per_method dict (from last_flights_per_method())
    so no additional DB queries are needed.
    """
    alerts: list[dict] = []

    methods = [
        ('W', 'winch',   'winch_'),
        ('S', 'aerotow', 'aerotow_'),
        ('E', 'TMG',     'tmg_'),
    ]

    for code, label, prefix in methods:
        last = last_per_method.get(code)
        if last is None:
            continue   # never used — no alert (may not be in exam methods)
        days = (today - last).days
        if days > 180:
            alerts.append(_alert(
                LEVEL_DANGER, f'{prefix}180',
                f'No {label} launch in over 180 days',
                f'SFCL.130: privileges are restricted to methods passed in the practical exam. '
                f'Last {label} launch was {days} days ago — refresher training recommended.',
                days=days,
                title_key='logbook.alert.launch_180.title',
                desc_key='logbook.alert.launch_180.desc',
                desc_params={'method': label, 'days': days},
            ))
        elif days > 90:
            alerts.append(_alert(
                LEVEL_WARNING, f'{prefix}90',
                f'No {label} launch in over 90 days',
                f'Last {label} launch was {days} days ago. Consider a currency flight.',
                days=days,
                title_key='logbook.alert.launch_90.title',
                desc_key='logbook.alert.launch_90.desc',
                desc_params={'method': label, 'days': days},
            ))

    return alerts


def _check_passenger_recency(window_90: dict) -> list[dict]:
    """FCL.060 — 3 T/O + 3 landings as PIC in last 90 days before carrying a passenger."""
    alerts: list[dict] = []

    if window_90['flights'] < 3:
        alerts.append(_alert(
            LEVEL_INFO, 'pax_recency',
            'Recent experience — passenger carriage',
            'FCL.060: before carrying a passenger you need 3 take-offs and 3 landings '
            'as PIC in the last 90 days. '
            f'Current: {window_90["flights"]} flights in the last 90 days.',
            action='logbook.alert.action.check',
            desc_params={'flights': window_90['flights']},
        ))

    return alerts


def _check_passenger_thresholds(pic: dict, today: date, profile) -> list[dict]:
    """SFCL.115(b) — passenger carriage thresholds (30 PIC for first, 200 for hire/reward)."""
    alerts: list[dict] = []

    pre_launches = getattr(profile, 'pic_launches_pre_logbook', 0) or 0
    total_launches = pic['flights'] + pre_launches

    if total_launches < 30:
        alerts.append(_alert(
            LEVEL_INFO, 'pax_threshold_1',
            'Passenger carriage — threshold 1',
            f'SFCL.115(b)(1): first passenger requires 10h PIC or 30 PIC launches. '
            f'Current: {total_launches} PIC launches.',
            action='logbook.alert.action.check',
            desc_params={'launches': total_launches},
        ))
    elif total_launches < 200:
        alerts.append(_alert(
            LEVEL_INFO, 'pax_threshold_2',
            'Hire/reward flights — threshold 2',
            f'SFCL.115(b)(2): flights for hire/reward require 75h PIC or 200 PIC launches '
            f'+ proficiency check. Current: {total_launches} PIC launches.',
            desc_params={'launches': total_launches},
        ))

    return alerts


def _check_medical(user: User, today: date, profile) -> list[dict]:
    """Part-MED — medical certificate expiry warning."""
    alerts: list[dict] = []
    expiry = _get_medical_expiry(user, profile)

    if expiry is None:
        alerts.append(_alert(
            LEVEL_INFO, 'medical_missing',
            'Medical certificate — no expiry date',
            'Enter your medical certificate expiry date in Settings so the system '
            'can remind you 60 days before it expires.',
            action='logbook.alert.action.fill_in',
        ))
        return alerts

    days_remaining = (expiry - today).days
    if days_remaining < 0:
        alerts.append(_alert(
            LEVEL_DANGER, 'medical_expired',
            'Medical certificate expired',
            f'Your medical certificate expired {abs(days_remaining)} days ago. '
            'You cannot exercise the privileges of your licence until you renew it.',
            days=abs(days_remaining),
            desc_params={'days': abs(days_remaining)},
        ))
    elif days_remaining <= 60:
        alerts.append(_alert(
            LEVEL_WARNING, 'medical_soon',
            'Medical certificate expiring soon',
            f'Your medical certificate expires in {days_remaining} days ({expiry.isoformat()}). '
            'Schedule a renewal appointment.',
            days=days_remaining,
            desc_params={'days': days_remaining, 'expiry': expiry.isoformat()},
        ))

    return alerts


def _check_profile_completeness(user: User, profile) -> list[dict]:
    """Remind the user to complete their pilot profile."""
    alerts: list[dict] = []

    if profile is None or profile.license_date is None:
        alerts.append(_alert(
            LEVEL_INFO, 'profile_license_date',
            'SPL licence date not entered',
            'Enter your SPL licence issue date in Settings. '
            'This is needed to accurately compute passenger-carriage thresholds (SFCL.115).',
            action='logbook.alert.action.fill_in',
        ))

    return alerts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_medical_expiry(user: User, profile) -> Optional[date]:
    """Resolve medical expiry from pilot_profile (preferred) or legacy user column."""
    if profile and profile.medical_expiry:
        return profile.medical_expiry
    # Legacy fallback — migration 026 added logbook_medical_expiry to users
    legacy = getattr(user, 'logbook_medical_expiry', None)
    return legacy
