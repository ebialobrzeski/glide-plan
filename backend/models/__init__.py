"""Models package — SQLAlchemy ORM models and legacy dataclasses."""
from backend.models.base import Base
from backend.models.user import User
from backend.models.waypoint_file import WaypointFile, WaypointEntry
from backend.models.task import SavedTask
from backend.models.legacy import Waypoint  # backwards-compat for file_io and app.py
from backend.models.i18n import Language, TranslationKey, Translation
from backend.models.connector import Connector
from backend.models.flight import Flight
from backend.models.sync_log import SyncLog
from backend.models.import_log import ImportLog
from backend.models.pilot_profile import PilotProfile

__all__ = ['Base', 'User', 'WaypointFile', 'WaypointEntry', 'SavedTask', 'Waypoint',
           'Language', 'TranslationKey', 'Translation',
           'Connector', 'Flight', 'SyncLog', 'ImportLog', 'PilotProfile']
