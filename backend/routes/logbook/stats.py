"""GlideLog — statistics API endpoints."""
from flask import jsonify
from flask_login import current_user

from backend.db import get_db
from backend.routes.logbook import logbook_bp
from backend.services.logbook import stats as stats_svc
from backend.utils.auth_decorators import login_required


@logbook_bp.route('/api/stats/summary', methods=['GET'])
@login_required
def stats_summary():
    return jsonify(stats_svc.summary(get_db(), current_user))


@logbook_bp.route('/api/stats/by-month', methods=['GET'])
@login_required
def stats_by_month():
    return jsonify(stats_svc.by_month(get_db(), current_user))


@logbook_bp.route('/api/stats/by-aircraft', methods=['GET'])
@login_required
def stats_by_aircraft():
    return jsonify(stats_svc.by_aircraft(get_db(), current_user))


@logbook_bp.route('/api/stats/by-launch-type', methods=['GET'])
@login_required
def stats_by_launch_type():
    return jsonify(stats_svc.by_launch_type(get_db(), current_user))


@logbook_bp.route('/api/stats/by-task', methods=['GET'])
@login_required
def stats_by_task():
    return jsonify(stats_svc.by_task(get_db(), current_user))
