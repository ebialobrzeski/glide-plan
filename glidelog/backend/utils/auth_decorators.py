"""Flask route decorators for authentication and authorisation."""
from __future__ import annotations

from functools import wraps
from typing import Callable
from urllib.parse import quote

from flask import jsonify, redirect, request
from flask_login import current_user

from backend.config import GLIDEPLAN_URL


def login_required(f: Callable) -> Callable:
    """Return 401 JSON if the request is not authenticated. Use for API routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required.'}), 401
        return f(*args, **kwargs)
    return decorated


def page_login_required(f: Callable) -> Callable:
    """Redirect unauthenticated visitors to the main GlidePlan app to log in.

    GlideLog has no login UI of its own, so the login prompt lives on the main
    app (GLIDEPLAN_URL). We pass the current URL as ?next so the user is sent
    back here once authenticated. Falls back to a relative redirect only when
    GLIDEPLAN_URL is unset (single-host/dev deployments).
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            next_url = quote(request.url, safe='')
            base = GLIDEPLAN_URL if GLIDEPLAN_URL else ''
            return redirect(f'{base}/?login=1&next={next_url}')
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
