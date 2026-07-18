"""GlideLog — pilot profile API endpoints."""
import logging
from datetime import date

from flask import jsonify, request
from flask_login import current_user

from backend.db import get_db
from backend.models.pilot_profile import PilotProfile
from backend.routes.logbook import logbook_bp
from backend.utils.auth_decorators import login_required

logger = logging.getLogger(__name__)


@logbook_bp.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    profile = getattr(current_user, 'pilot_profile', None)
    if profile is None:
        return jsonify({})
    return jsonify(profile.to_dict())


@logbook_bp.route('/api/profile', methods=['PATCH'])
@login_required
def update_profile():
    db = get_db()
    data = request.get_json(silent=True) or {}

    profile = getattr(current_user, 'pilot_profile', None)
    if profile is None:
        profile = PilotProfile(user_id=current_user.id)
        db.add(profile)

    def _parse_date(val):
        if not val:
            return None
        try:
            return date.fromisoformat(val)
        except (ValueError, TypeError):
            return None

    if 'medical_expiry' in data:
        profile.medical_expiry = _parse_date(data['medical_expiry'])
    if 'license_date' in data:
        profile.license_date = _parse_date(data['license_date'])

    try:
        db.commit()
        db.refresh(profile)
        return jsonify(profile.to_dict())
    except Exception:
        db.rollback()
        logger.exception('Failed to update pilot profile')
        return jsonify({'error': 'Failed to save profile.'}), 500
