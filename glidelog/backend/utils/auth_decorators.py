"""Flask route decorators for authentication and authorisation."""
from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import jsonify, redirect, request, url_for
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
    """Redirect to login page if the request is not authenticated. Use for HTML page routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            next_url = request.url
            return redirect(f'/?login=1&next={next_url}')
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
