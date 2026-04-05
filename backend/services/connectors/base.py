"""BaseConnector — interface every connector must implement."""
from __future__ import annotations

import base64
import logging
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


def _fernet_from_secret(secret_key: str) -> Fernet:
    key_bytes = secret_key.encode()[:32].ljust(32, b'\0')
    return Fernet(base64.urlsafe_b64encode(key_bytes))


class BaseConnector(ABC):
    """Strategy interface for all external flight data sources."""

    def __init__(self, db_record) -> None:
        self._record = db_record

    def _decrypt(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        from backend.config import SECRET_KEY
        try:
            f = _fernet_from_secret(SECRET_KEY)
            return f.decrypt(value.encode()).decode()
        except Exception:
            logger.exception('Failed to decrypt connector credential')
            return None

    @staticmethod
    def encrypt(value: str) -> str:
        from backend.config import SECRET_KEY
        f = _fernet_from_secret(SECRET_KEY)
        return f.encrypt(value.encode()).decode()

    @abstractmethod
    def test_connection(self) -> bool:
        """Return True if credentials are valid and the source is reachable."""

    @abstractmethod
    def fetch_flights(self, date_from: date, date_to: date) -> list[dict]:
        """Return a list of raw flight dicts for the given date range."""

    def get_display_name(self) -> str:
        return self._record.display_name
