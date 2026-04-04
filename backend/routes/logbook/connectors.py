"""GlideLog — connectors API endpoints."""
import logging
import threading

from flask import jsonify, request
from flask_login import current_user

from backend.db import get_db
from backend.models.connector import Connector
from backend.models.sync_log import SyncLog
from backend.routes.logbook import logbook_bp
from backend.services.connectors import get_connector
from backend.services.connectors.base import BaseConnector
from backend.services.logbook.sync import sync_connector
from backend.utils.auth_decorators import login_required

logger = logging.getLogger(__name__)


@logbook_bp.route('/api/connectors', methods=['GET'])
@login_required
def list_connectors():
    db = get_db()
    connectors = db.query(Connector).filter(Connector.user_id == current_user.id).all()
    return jsonify([c.to_dict(include_credentials=True) for c in connectors])


@logbook_bp.route('/api/connectors', methods=['POST'])
@login_required
def create_connector():
    db = get_db()
    data = request.get_json(silent=True) or {}
    ctype = data.get('type', '').strip()
    if ctype not in ('echrono', 'leonardo', 'weglide', 'seeyou', 'manual'):
        return jsonify({'error': 'Invalid connector type.'}), 400
    if not data.get('display_name', '').strip():
        return jsonify({'error': 'display_name is required.'}), 400

    try:
        connector = Connector(
            user_id=current_user.id,
            type=ctype,
            display_name=data['display_name'].strip(),
            base_url=data.get('base_url'),
            config=data.get('config'),
        )
        if data.get('login'):
            connector.login_encrypted = BaseConnector.encrypt(data['login'])
        if data.get('password'):
            connector.password_encrypted = BaseConnector.encrypt(data['password'])
        db.add(connector)
        db.commit()
        return jsonify(connector.to_dict(include_credentials=True)), 201
    except Exception:
        db.rollback()
        logger.exception('Failed to create connector')
        return jsonify({'error': 'Failed to create connector.'}), 500


@logbook_bp.route('/api/connectors/<connector_id>', methods=['PUT'])
@login_required
def update_connector(connector_id):
    db = get_db()
    connector = _get_connector_or_404(db, connector_id)
    if not connector:
        return jsonify({'error': 'Connector not found.'}), 404

    data = request.get_json(silent=True) or {}
    try:
        if 'display_name' in data:
            connector.display_name = data['display_name'].strip()
        if 'base_url' in data:
            connector.base_url = data['base_url']
        if 'config' in data:
            connector.config = data['config']
        if 'is_active' in data:
            connector.is_active = bool(data['is_active'])
        if data.get('login'):
            connector.login_encrypted = BaseConnector.encrypt(data['login'])
        if data.get('password'):
            connector.password_encrypted = BaseConnector.encrypt(data['password'])
        db.commit()
        return jsonify(connector.to_dict(include_credentials=True))
    except Exception:
        db.rollback()
        logger.exception('Failed to update connector')
        return jsonify({'error': 'Failed to update connector.'}), 500


@logbook_bp.route('/api/connectors/<connector_id>', methods=['DELETE'])
@login_required
def delete_connector(connector_id):
    db = get_db()
    connector = _get_connector_or_404(db, connector_id)
    if not connector:
        return jsonify({'error': 'Connector not found.'}), 404
    try:
        db.delete(connector)
        db.commit()
        return '', 204
    except Exception:
        db.rollback()
        logger.exception('Failed to delete connector')
        return jsonify({'error': 'Failed to delete connector.'}), 500


@logbook_bp.route('/api/connectors/<connector_id>/test', methods=['POST'])
@login_required
def test_connector(connector_id):
    db = get_db()
    connector = _get_connector_or_404(db, connector_id)
    if not connector:
        return jsonify({'error': 'Connector not found.'}), 404
    try:
        impl = get_connector(connector)
        ok = impl.test_connection()
        return jsonify({'success': ok})
    except NotImplementedError:
        return jsonify({'error': 'This connector type is not yet implemented.'}), 501
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)})


@logbook_bp.route('/api/connectors/<connector_id>/sync', methods=['POST'])
@login_required
def trigger_sync(connector_id):
    db = get_db()
    connector = _get_connector_or_404(db, connector_id)
    if not connector:
        return jsonify({'error': 'Connector not found.'}), 404

    def _run():
        from backend.db import get_db as _get_db
        _db = _get_db()
        try:
            c = _db.query(Connector).filter(Connector.id == connector_id).first()
            if c:
                sync_connector(_db, c)  # commits internally
        except Exception:
            try:
                _db.rollback()
            except Exception:
                pass
            logger.exception('Triggered sync failed for connector %s', connector_id)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({'message': 'Sync started.'}), 202


@logbook_bp.route('/api/connectors/<connector_id>/status', methods=['GET'])
@login_required
def connector_status(connector_id):
    db = get_db()
    connector = _get_connector_or_404(db, connector_id)
    if not connector:
        return jsonify({'error': 'Connector not found.'}), 404
    last_log = (
        db.query(SyncLog)
        .filter(SyncLog.connector_id == connector.id)
        .order_by(SyncLog.started_at.desc())
        .first()
    )
    return jsonify({
        'connector': connector.to_dict(),
        'last_sync': last_log.to_dict() if last_log else None,
    })


@logbook_bp.route('/api/sync/status', methods=['GET'])
@login_required
def sync_status():
    db = get_db()
    last_log = (
        db.query(SyncLog)
        .filter(SyncLog.user_id == current_user.id)
        .order_by(SyncLog.started_at.desc())
        .first()
    )
    return jsonify({'last_sync': last_log.to_dict() if last_log else None})


@logbook_bp.route('/api/sync/history', methods=['GET'])
@login_required
def sync_history():
    db = get_db()
    logs = (
        db.query(SyncLog)
        .filter(SyncLog.user_id == current_user.id)
        .order_by(SyncLog.started_at.desc())
        .limit(50)
        .all()
    )
    return jsonify([l.to_dict() for l in logs])


def _get_connector_or_404(db, connector_id):
    return db.query(Connector).filter(
        Connector.id == connector_id,
        Connector.user_id == current_user.id,
    ).first()
