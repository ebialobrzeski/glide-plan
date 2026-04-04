"""SeeYouConnector — stub for SeeYou Cloud integration."""
from __future__ import annotations

from datetime import date

from backend.services.connectors.base import BaseConnector


class SeeYouConnector(BaseConnector):
    def test_connection(self) -> bool:
        raise NotImplementedError('SeeYou connector not yet implemented')

    def fetch_flights(self, date_from: date, date_to: date) -> list[dict]:
        raise NotImplementedError('SeeYou connector not yet implemented')
