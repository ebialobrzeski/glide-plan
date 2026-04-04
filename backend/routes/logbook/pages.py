"""GlideLog — HTML page routes (Jinja2 templates)."""
from flask import redirect, render_template, url_for
from flask_login import current_user

from backend.db import get_db
from backend.routes.logbook import logbook_bp
from backend.services.logbook import alerts as alerts_svc
from backend.services.logbook import stats as stats_svc
from backend.utils.auth_decorators import login_required


@logbook_bp.route('/', methods=['GET'])
@login_required
def index():
    return redirect(url_for('logbook.dashboard'))


@logbook_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    db = get_db()
    summary = stats_svc.summary(db, current_user)
    active_alerts = alerts_svc.get_alerts(db, current_user)
    monthly = stats_svc.by_month(db, current_user)
    by_aircraft = stats_svc.by_aircraft(db, current_user)
    return render_template(
        'logbook/dashboard.html',
        summary=summary,
        alerts=active_alerts,
        monthly_data=monthly,
        aircraft_data=by_aircraft,
    )


@logbook_bp.route('/flights', methods=['GET'])
@login_required
def flights_page():
    return render_template('logbook/flights.html')


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
    return render_template('logbook/settings.html')


@logbook_bp.route('/admin', methods=['GET'])
@login_required
def admin_page():
    if current_user.tier != 'admin':
        from flask import jsonify
        return jsonify({'error': 'Admin access required.'}), 403
    return render_template('logbook/admin.html')
