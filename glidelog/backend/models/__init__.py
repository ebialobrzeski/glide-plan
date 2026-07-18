"""Models package — imported for its side effect of registering every ORM
class on the shared declarative Base so that string-based relationships
(e.g. relationship('Flight')) resolve at mapper-configuration time.
"""
from backend.models.base import Base
from backend.models.user import User
from backend.models.i18n import Language, TranslationKey, Translation
from backend.models.connector import Connector
from backend.models.flight import Flight
from backend.models.sync_log import SyncLog
from backend.models.import_log import ImportLog
from backend.models.pilot_profile import PilotProfile
from backend.models.fun_stats_cache import FunStatsCache

__all__ = [
    'Base', 'User', 'Language', 'TranslationKey', 'Translation',
    'Connector', 'Flight', 'SyncLog', 'ImportLog', 'PilotProfile',
    'FunStatsCache',
]
