"""GlideLog — alerts API endpoint."""
from flask import jsonify
from flask_login import current_user

from backend.db import get_db
from backend.routes.logbook import logbook_bp
from backend.services.logbook import alerts as alerts_svc
from backend.utils.auth_decorators import login_required


@logbook_bp.route('/api/alerts', methods=['GET'])
@login_required
def get_alerts():
    return jsonify(alerts_svc.get_alerts(get_db(), current_user))
