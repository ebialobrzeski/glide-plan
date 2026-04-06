"""GlideLog — HTML page routes (Jinja2 templates)."""
from datetime import date

from flask import redirect, render_template, request, url_for
from flask_login import current_user

from backend.db import get_db
from backend.models.flight import Flight
from backend.routes.logbook import logbook_bp
from backend.services.logbook import alerts as alerts_svc
from backend.services.logbook import stats as stats_svc
from backend.utils.auth_decorators import page_login_required as login_required


def _current_season_year() -> int:
    today = date.today()
    # Soaring season: April–October.  Before April → previous year's season.
    return today.year if today.month >= 4 else today.year - 1


def _active_season_year(db, user) -> int:
    """Return the season year to display.

    Prefers the current season if it has flights; otherwise falls back to
    the season of the user's most recent flight.
    """
    current_year = _current_season_year()
    current_start = date(current_year, 4, 1)
    current_end   = date(current_year, 10, 31)

    has_current = db.query(Flight).filter(
        Flight.user_id == user.id,
        Flight.date.isnot(None),
        Flight.date >= current_start,
        Flight.date <= current_end,
    ).first() is not None

    if has_current:
        return current_year

    # Fall back to the season of the most recent flight
    # Filter out NULL dates — PostgreSQL sorts NULLs first on DESC, which
    # would otherwise make latest = None and incorrectly return current_year.
    latest_row = db.query(Flight.date).filter(
        Flight.user_id == user.id,
        Flight.date.isnot(None),
    ).order_by(Flight.date.desc()).first()
    latest = latest_row[0] if latest_row is not None else None

    if latest is None:
        return current_year  # no flights at all — show current empty season

    # Determine which season that date belongs to
    if latest.month >= 4:
        return latest.year
    return latest.year - 1


@logbook_bp.route('/', methods=['GET'])
@login_required
def index():
    return redirect(url_for('logbook.dashboard'))


@logbook_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    db = get_db()
    year = _active_season_year(db, current_user)
    season_start = date(year, 4, 1)
    season_end   = date(year, 10, 31)

    summary        = stats_svc.summary(db, current_user)
    season_summary = stats_svc.summary_season(db, current_user, year)
    active_alerts  = alerts_svc.get_alerts(db, current_user)
    monthly        = stats_svc.by_month(db, current_user,
                                        date_from=season_start, date_to=season_end)
    monthly_launch = stats_svc.by_month_and_launch(db, current_user,
                                                   date_from=season_start, date_to=season_end)
    by_aircraft    = stats_svc.by_aircraft(db, current_user,
                                           date_from=season_start, date_to=season_end)
    instructors    = stats_svc.by_instructor(db, current_user,
                                             date_from=season_start, date_to=season_end)
    winch_ops      = stats_svc.by_winch_operator(db, current_user,
                                                 date_from=season_start, date_to=season_end)
    top_flights    = stats_svc.longest_flights(db, current_user, limit=5,
                                              date_from=season_start, date_to=season_end)
    facts          = stats_svc.fun_facts(db, current_user,
                                         date_from=season_start, date_to=season_end)
    weekly         = stats_svc.weekly_activity(db, current_user)

    return render_template(
        'logbook/dashboard.html',
        season_year=year,
        summary=summary,
        season=season_summary,
        alerts=active_alerts,
        monthly_data=monthly,
        monthly_launch_data=monthly_launch,
        aircraft_data=by_aircraft,
        instructors=instructors,
        winch_ops=winch_ops,
        top_flights=top_flights,
        facts=facts,
        weekly=weekly,
    )


@logbook_bp.route('/statistics', methods=['GET'])
@login_required
def statistics_page():
    db = get_db()
    year = _active_season_year(db, current_user)

    # Default: all-time (no date filter). Only restrict when the user explicitly
    # provides both query params.
    raw_from = request.args.get('date_from', '').strip()
    raw_to   = request.args.get('date_to',   '').strip()

    date_from: date | None = None
    date_to:   date | None = None
    try:
        if raw_from:
            date_from = date.fromisoformat(raw_from)
    except ValueError:
        pass
    try:
        if raw_to:
            date_to = date.fromisoformat(raw_to)
    except ValueError:
        pass

    is_filtered = bool(date_from or date_to)

    # KPI summary: use range if filtered, otherwise all-time
    all_time = stats_svc.summary(db, current_user)
    if is_filtered:
        _df = date_from or date(2000, 1, 1)
        _dt = date_to   or date.today()
        period_summary = stats_svc.summary_range(db, current_user, _df, _dt)
    else:
        period_summary = all_time

    monthly_launch   = stats_svc.by_month_and_launch(db, current_user,
                                                     date_from=date_from, date_to=date_to)
    monthly_aircraft = stats_svc.by_month_and_aircraft(db, current_user,
                                                       date_from=date_from, date_to=date_to)
    monthly_data   = stats_svc.by_month(db, current_user,
                                        date_from=date_from, date_to=date_to)
    by_aircraft    = stats_svc.by_aircraft(db, current_user,
                                           date_from=date_from, date_to=date_to)
    by_launch      = stats_svc.by_launch_type(db, current_user,
                                              date_from=date_from, date_to=date_to)
    active_alerts  = alerts_svc.get_alerts(db, current_user)
    top_flights    = stats_svc.longest_flights(db, current_user, limit=5,
                                              date_from=date_from, date_to=date_to)
    instructors    = stats_svc.by_instructor(db, current_user,
                                             date_from=date_from, date_to=date_to)
    winch_ops      = stats_svc.by_winch_operator(db, current_user,
                                                 date_from=date_from, date_to=date_to)
    facts          = stats_svc.fun_facts(db, current_user,
                                         date_from=date_from, date_to=date_to)
    weekly         = stats_svc.weekly_activity(db, current_user)

    return render_template(
        'logbook/statistics.html',
        season_year=year,
        period=period_summary,
        summary=all_time,
        monthly_launch_data=monthly_launch,
        monthly_aircraft_data=monthly_aircraft,
        monthly_data=monthly_data,
        aircraft_data=by_aircraft,
        launch_data=by_launch,
        alerts=active_alerts,
        top_flights=top_flights,
        instructors=instructors,
        winch_ops=winch_ops,
        facts=facts,
        weekly=weekly,
        date_from_str=date_from.isoformat() if date_from else '',
        date_to_str=date_to.isoformat() if date_to else '',
        is_filtered=is_filtered,
    )


@logbook_bp.route('/licenses', methods=['GET'])
@login_required
def licenses_page():
    db = get_db()
    currency   = alerts_svc.get_currency_summary(db, current_user)
    alerts     = alerts_svc.get_alerts(db, current_user)
    winch_ops  = stats_svc.by_winch_operator(db, current_user)
    window_90  = stats_svc.flights_in_window(db, current_user, window_days=90)
    pic_totals = stats_svc.pic_totals(db, current_user)

    return render_template(
        'logbook/licenses.html',
        currency=currency,
        alerts=alerts,
        winch_ops=winch_ops,
        window_90=window_90,
        pic_totals=pic_totals,
    )


@logbook_bp.route('/flights', methods=['GET'])
@login_required
def flights_page():
    return render_template('logbook/flights.html')


@logbook_bp.route('/fun-stats', methods=['GET'])
@login_required
def fun_stats_page():
    return render_template('logbook/fun_stats.html')


@logbook_bp.route('/connectors', methods=['GET'])
@login_required
def connectors_page():
    return render_template('logbook/connectors.html')


@logbook_bp.route('/import', methods=['GET'])
@login_required
def import_page():
    return render_template('logbook/import.html')


@logbook_bp.route('/settings', methods=['GET'])
@login_required
def settings_page():
    profile = getattr(current_user, 'pilot_profile', None)
    return render_template('logbook/settings.html', profile=profile)


@logbook_bp.route('/admin', methods=['GET'])
@login_required
def admin_page():
    if current_user.tier != 'admin':
        from flask import jsonify
        return jsonify({'error': 'Admin access required.'}), 403
    return render_template('logbook/admin.html')
