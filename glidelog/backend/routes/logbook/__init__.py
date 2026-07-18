"""GlideLog blueprint — flight logbook module."""
from flask import Blueprint

logbook_bp = Blueprint('logbook', __name__, url_prefix='/logbook')

from backend.routes.logbook import pages, flights, connectors, stats, alerts, import_, admin, fun_stats, profile  # noqa: E402, F401
