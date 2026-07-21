"""Authentication blueprint — /auth/*

GlideLog authenticates users directly (its own login/registration popup)
against the shared `users` table, rather than redirecting to the main
GlidePlan app. The logic mirrors GlidePlan's own /auth endpoints so a session
created here is identical to one created there.
"""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_user, logout_user

from backend.db import get_db
from backend.models.user import User
from backend.services import auth_service, user_service
from backend.services.auth_service import AuthError, EmailNotVerifiedError
from backend.services.email_service import send_verification_code
from backend.utils.auth_decorators import login_required

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# The auth service raises AuthError with these fixed, human-readable messages
# (or frontend-mapped codes). Echoing a caught exception's text straight back to
# the client risks leaking internal detail (CWE-209), so we only ever return a
# value drawn from this allow-list — the returned string comes from the constant
# set, never from the exception object.
_SAFE_AUTH_ERRORS = frozenset({
    'Invalid email address.',
    'Password must be at least 8 characters.',
    'Display name must be between 2 and 100 characters.',
    'An account with that email already exists.',
    'Current password is incorrect.',
    'code_invalid',
    'code_expired',
    'too_many_attempts',
})


def _safe_auth_error(exc: AuthError, default: str) -> str:
    """Return the exception's message only if it is a known-safe value."""
    text = str(exc)
    for known in _SAFE_AUTH_ERRORS:
        if text == known:
            return known
    return default


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    email = data.get('email', '')
    display_name = data.get('display_name', '')
    password = data.get('password', '')

    if not email or not display_name or not password:
        return jsonify({'error': 'email, display_name, and password are required.'}), 400

    db = get_db()
    try:
        user = auth_service.register_user(db, email, display_name, password)
        code = auth_service.generate_verification_code(db, user)
        db.commit()
        send_verification_code(user.email, code, user.display_name)
        return jsonify({'requires_verification': True, 'email': user.email}), 201
    except AuthError as exc:
        db.rollback()
        return jsonify({'error': _safe_auth_error(exc, 'Registration failed.')}), 409
    except Exception:
        db.rollback()
        logger.exception('Unexpected error during registration')
        return jsonify({'error': 'Registration failed.'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get('email', '')
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'email and password are required.'}), 400

    db = get_db()
    try:
        user = auth_service.authenticate(db, email, password)
        if user is None:
            return jsonify({'error': 'Invalid email or password.'}), 401
        db.commit()
        login_user(user, remember=True)
        limits = user_service.get_tier_limits(user.tier)
        return jsonify({'user': user.to_dict(), 'limits': limits})
    except EmailNotVerifiedError as exc:
        # Correct credentials but unverified — send a fresh code and prompt
        unverified = db.query(User).filter(User.email == exc.email).first()
        if unverified:
            code = auth_service.generate_verification_code(db, unverified)
            db.commit()
            send_verification_code(exc.email, code, unverified.display_name)
        return jsonify({'requires_verification': True, 'email': exc.email})
    except Exception:
        db.rollback()
        logger.exception('Unexpected error during login')
        return jsonify({'error': 'Login failed.'}), 500


@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """Verify a user's email with the OTP code. Logs the user in on success."""
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    code = data.get('code', '').strip()

    if not email or not code:
        return jsonify({'error': 'email and code are required.'}), 400

    db = get_db()
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        return jsonify({'error': 'code_invalid'}), 400

    try:
        auth_service.verify_email_code(db, user, code)
        db.commit()
        login_user(user, remember=True)
        limits = user_service.get_tier_limits(user.tier)
        return jsonify({'user': user.to_dict(), 'limits': limits})
    except AuthError as exc:
        db.commit()  # persist attempt count increment
        return jsonify({'error': _safe_auth_error(exc, 'code_invalid')}), 400
    except Exception:
        db.rollback()
        logger.exception('Unexpected error during email verification')
        return jsonify({'error': 'Verification failed.'}), 500


@auth_bp.route('/resend-code', methods=['POST'])
def resend_code():
    """Resend a verification code. Always returns 200 to avoid leaking account existence."""
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()

    if email:
        db = get_db()
        user = db.query(User).filter(User.email == email).first()
        if user and user.is_active and not user.email_verified:
            code = auth_service.generate_verification_code(db, user)
            db.commit()
            send_verification_code(user.email, code, user.display_name)

    return jsonify({}), 200


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return '', 204


@auth_bp.route('/me', methods=['GET'])
@login_required
def me():
    limits = user_service.get_tier_limits(current_user.tier)
    return jsonify({'user': current_user.to_dict(), 'limits': limits})
