"""GlideLog — admin API endpoints."""
import logging

from flask import jsonify, request
from flask_login import current_user

from backend.db import get_db
from backend.models.flight import Flight
from backend.models.user import User
from backend.routes.logbook import logbook_bp
from backend.utils.auth_decorators import admin_required

logger = logging.getLogger(__name__)


@logbook_bp.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_list_users():
    db = get_db()
    users = db.query(User).order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users])


@logbook_bp.route('/api/admin/users/<user_id>', methods=['PATCH'])
@admin_required
def admin_patch_user(user_id):
    db = get_db()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return jsonify({'error': 'User not found.'}), 404
    data = request.get_json(silent=True) or {}
    try:
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
        if 'logbook_enabled' in data:
            user.logbook_enabled = bool(data['logbook_enabled'])
        db.commit()
        return jsonify(user.to_dict())
    except Exception:
        db.rollback()
        logger.exception('Failed to patch user')
        return jsonify({'error': 'Failed to update user.'}), 500


@logbook_bp.route('/api/admin/users/<user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    if str(current_user.id) == user_id:
        return jsonify({'error': 'Cannot delete yourself.'}), 400
    db = get_db()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return jsonify({'error': 'User not found.'}), 404
    try:
        db.delete(user)
        db.commit()
        return '', 204
    except Exception:
        db.rollback()
        logger.exception('Failed to delete user')
        return jsonify({'error': 'Failed to delete user.'}), 500


@logbook_bp.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    db = get_db()
    from sqlalchemy import func
    rows = (
        db.query(
            Flight.user_id,
            func.count(Flight.id).label('flights'),
            func.coalesce(func.sum(Flight.flight_time_min), 0).label('minutes'),
        )
        .group_by(Flight.user_id)
        .all()
    )
    users = {str(u.id): u.display_name for u in db.query(User).all()}
    return jsonify([
        {
            'user_id': str(r.user_id),
            'display_name': users.get(str(r.user_id), ''),
            'flights': r.flights,
            'minutes': int(r.minutes),
        }
        for r in rows
    ])
