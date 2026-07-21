"""Flask route decorators for authentication and authorisation."""
from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import jsonify, render_template, request
from flask_login import current_user


def login_required(f: Callable) -> Callable:
    """Return 401 JSON if the request is not authenticated. Use for API routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required.'}), 401
        return f(*args, **kwargs)
    return decorated


def page_login_required(f: Callable) -> Callable:
    """Render GlideLog's own login/registration popup for unauthenticated visitors.

    GlideLog now authenticates users itself (shared users table, shared
    SECRET_KEY) instead of bouncing them to the main GlidePlan app. The login
    page is served in place at the requested URL so that, after a successful
    login, the browser can return straight to where the visitor was headed.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return render_template('logbook/login.html', next_url=request.url), 401
        return f(*args, **kwargs)
    return decorated


def premium_required(f: Callable) -> Callable:
    """Return 403 if the authenticated user is not premium or admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required.'}), 401
        if current_user.tier not in ('premium', 'admin'):
            return jsonify({'error': 'Premium subscription required.'}), 403
        return f(*args, **kwargs)
    return decorated


def admin_required(f: Callable) -> Callable:
    """Return 403 if the authenticated user is not an admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required.'}), 401
        if current_user.tier != 'admin':
            return jsonify({'error': 'Admin access required.'}), 403
        return f(*args, **kwargs)
    return decorated
