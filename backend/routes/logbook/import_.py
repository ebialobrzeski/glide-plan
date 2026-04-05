"""GlideLog — file import API endpoints."""
import logging
import os
import tempfile

from flask import jsonify, request, session
from flask_login import current_user
from werkzeug.utils import secure_filename

from backend.db import get_db
from backend.models.import_log import ImportLog
from backend.routes.logbook import logbook_bp
from backend.services.logbook import import_service
from backend.utils.auth_decorators import login_required

logger = logging.getLogger(__name__)

_UPLOAD_SESSION_KEY = 'logbook_upload'
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


@logbook_bp.route('/api/import/upload', methods=['POST'])
@login_required
def import_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided.'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'error': 'Empty filename.'}), 400

    source_type = request.form.get('source_type', 'csv').strip()
    if source_type not in import_service.SUPPORTED_SOURCES:
        return jsonify({'error': f'Unsupported source type: {source_type}'}), 400

    content = f.read(_MAX_UPLOAD_BYTES + 1)
    if len(content) > _MAX_UPLOAD_BYTES:
        return jsonify({'error': 'File too large (max 10 MB).'}), 413

    filename = secure_filename(f.filename)
    # Store in session temporarily (small files), or temp file for larger ones
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1])
    tmp.write(content)
    tmp.close()

    upload_id = tmp.name
    session[_UPLOAD_SESSION_KEY] = {
        'upload_id': upload_id,
        'source_type': source_type,
        'filename': filename,
    }
    return jsonify({'upload_id': upload_id, 'filename': filename, 'source_type': source_type})


@logbook_bp.route('/api/import/preview', methods=['POST'])
@login_required
def import_preview():
    meta = session.get(_UPLOAD_SESSION_KEY)
    if not meta:
        return jsonify({'error': 'No upload in progress. Upload a file first.'}), 400

    try:
        with open(meta['upload_id'], 'rb') as fh:
            content = fh.read()
        db = get_db()
        result = import_service.preview(db, current_user, meta['source_type'], content)
        return jsonify(result)
    except import_service.ImportServiceError as e:
        return jsonify({'error': str(e)}), 400
    except Exception:
        logger.exception('Import preview failed')
        return jsonify({'error': 'Failed to preview import.'}), 500


@logbook_bp.route('/api/import/confirm', methods=['POST'])
@login_required
def import_confirm():
    meta = session.get(_UPLOAD_SESSION_KEY)
    if not meta:
        return jsonify({'error': 'No upload in progress. Upload a file first.'}), 400

    data = request.get_json(silent=True) or {}
    new_rows = data.get('new', [])

    try:
        with open(meta['upload_id'], 'rb') as fh:
            content = fh.read()  # noqa — kept for re-validation if needed

        db = get_db()
        log = import_service.confirm(
            db,
            current_user,
            meta['source_type'],
            new_rows,
            filename=meta.get('filename'),
        )
        db.commit()

        # Clean up temp file and session
        try:
            os.unlink(meta['upload_id'])
        except OSError:
            pass
        session.pop(_UPLOAD_SESSION_KEY, None)

        return jsonify(log.to_dict()), 201
    except import_service.ImportServiceError as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception:
        db.rollback()
        logger.exception('Import confirm failed')
        return jsonify({'error': 'Failed to confirm import.'}), 500


@logbook_bp.route('/api/import/history', methods=['GET'])
@login_required
def import_history():
    db = get_db()
    logs = (
        db.query(ImportLog)
        .filter(ImportLog.user_id == current_user.id)
        .order_by(ImportLog.imported_at.desc())
        .limit(50)
        .all()
    )
    return jsonify([l.to_dict() for l in logs])
