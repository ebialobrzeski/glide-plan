"""
Flask web application for GlideLog — the standalone flight logbook.

GlideLog runs as its own container/service but shares the GlidePlan
PostgreSQL database (users, languages, translations, logbook tables) and the
login session cookie (signed with the same SECRET_KEY). It exposes no auth UI
of its own: unauthenticated visitors are bounced to the main GlidePlan app to
log in, then return here with a valid session cookie.
"""
import io
import os
import sys
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify, redirect, request
from flask_cors import CORS
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

# backend.config loads dotenv from .env at import time
from backend.config import SECRET_KEY, FLASK_DEBUG, GLIDEPLAN_URL, SESSION_COOKIE_DOMAIN
from backend.db import init_db, get_db
# Import the models package for its registration side effect so every ORM
# class is known to the shared Base before any query runs.
import backend.models  # noqa: F401
from backend.models.user import User
from backend.routes.logbook import logbook_bp
from backend.routes.i18n import i18n_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Behind Cloudflare / a reverse proxy, trust the forwarded proto and host so
# request.url reports https://<public-host>/… instead of http://<internal>.
# Without this the ?next= redirect target is built with the wrong scheme.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

INSECURE_SECRET_KEYS = {'CHANGE-ME-IN-PRODUCTION', 'CHANGE-ME', 'change_this_secret_key_in_production'}
if app.secret_key in INSECURE_SECRET_KEYS:
    if FLASK_DEBUG:
        import warnings
        warnings.warn('SECRET_KEY is not set. Set SECRET_KEY environment variable in production.', stacklevel=1)
    else:
        raise RuntimeError(
            'SECRET_KEY is not set to a secure value. Refusing to start outside debug mode. '
            'It MUST match the main GlidePlan app so the login session cookie is shared. '
            'Set the SECRET_KEY environment variable to the same random secret used by GlidePlan.'
        )

# Session cookie must be readable by the main app — share the signing key
# (SECRET_KEY, above) and, when on different subdomains, the cookie domain.
if SESSION_COOKIE_DOMAIN:
    app.config['SESSION_COOKIE_DOMAIN'] = SESSION_COOKIE_DOMAIN

CORS(app)

# ── Flask-Login ──────────────────────────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.session_protection = 'strong'


@login_manager.user_loader
def load_user(user_id: str):
    try:
        import uuid
        uid = uuid.UUID(user_id)
    except (ValueError, AttributeError, TypeError):
        return None
    try:
        return get_db().query(User).filter(User.id == uid, User.is_active == True).first()  # noqa: E712
    except Exception:
        return None


@login_manager.unauthorized_handler
def unauthorized():
    """API routes get 401 JSON; page routes redirect to the main app's login."""
    if request.path.startswith('/api/') or request.headers.get('Accept', '').startswith('application/json'):
        return jsonify({'error': 'Authentication required.'}), 401
    login_url = f'{GLIDEPLAN_URL}/?login=1&next={request.url}' if GLIDEPLAN_URL else '/?login=1'
    return redirect(login_url)


# ── Template context — expose the main app URL for cross-app links ────────────
@app.context_processor
def inject_glideplan_url():
    return {'GLIDEPLAN_URL': GLIDEPLAN_URL}


# ── Blueprints ───────────────────────────────────────────────────────────────
app.register_blueprint(logbook_bp)
app.register_blueprint(i18n_bp)

# ── Database ─────────────────────────────────────────────────────────────────
# Migrations for the logbook tables (026-037) are owned by the main GlidePlan
# app and already applied to the shared database. init_db() runs any pending
# migrations idempotently against the shared schema_migrations ledger, so this
# is a no-op unless GlideLog is pointed at a fresh database.
init_db(app)

# ── Root redirect ─────────────────────────────────────────────────────────────
@app.route('/')
def index():
    """GlideLog has no landing page of its own — send visitors to the logbook."""
    return redirect('/logbook/dashboard')


@app.route('/health')
def health_check():
    """Health check endpoint for container monitoring."""
    from backend.db import is_db_available, get_engine

    health_status = {'status': 'healthy', 'timestamp': datetime.now().isoformat()}

    if get_engine() is None:
        health_status['database'] = 'not configured'
    elif is_db_available():
        health_status['database'] = 'reachable'
    else:
        health_status['database'] = 'unreachable'
        health_status['status'] = 'unhealthy'
        app.logger.error('Database unreachable during health check')

    status_code = 200 if health_status['status'] == 'healthy' else 503
    return jsonify(health_status), status_code


# ── GlideLog background scheduler ────────────────────────────────────────────
from backend.config import GLIDELOG_SCHEDULER_ENABLED
if GLIDELOG_SCHEDULER_ENABLED:
    _is_reloader_child = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    _is_production = not app.debug
    if _is_reloader_child or _is_production:
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from backend.services.logbook.sync import sync_all_users
            _scheduler = BackgroundScheduler(
                job_defaults={'coalesce': True, 'max_instances': 1}
            )

            @_scheduler.scheduled_job('interval', hours=24, id='glidelog_sync_all')
            def _glidelog_sync_job():
                try:
                    sync_all_users(get_db())
                except Exception:
                    logging.getLogger(__name__).exception('GlideLog scheduled sync failed')

            _scheduler.start()
            import atexit
            atexit.register(lambda: _scheduler.shutdown(wait=False))
            app.logger.info('GlideLog scheduler started')
        except ImportError:
            app.logger.warning('APScheduler not installed — GlideLog background sync disabled.')

# ── Logging ──────────────────────────────────────────────────────────────────
os.makedirs('logs', exist_ok=True)

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

file_handler = RotatingFileHandler('logs/glidelog.log', maxBytes=10485760, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s [%(name)s] %(message)s [%(pathname)s:%(lineno)d]'
))
if app.debug:
    file_handler.setLevel(logging.DEBUG)
    _console = logging.StreamHandler()
    _console.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s'))
    _console.setLevel(logging.DEBUG)
    logging.getLogger('backend').addHandler(_console)
    logging.getLogger('backend').setLevel(logging.DEBUG)
else:
    file_handler.setLevel(logging.INFO)

app.logger.addHandler(file_handler)
app.logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
logging.getLogger('backend').addHandler(file_handler)

app.logger.info('GlideLog startup (debug=%s)', app.debug)


if __name__ == '__main__':
    app.run(debug=FLASK_DEBUG, host='0.0.0.0', port=5001)
