"""WeGlideConnector — stub for WeGlide integration."""
from __future__ import annotations

from datetime import date

from backend.services.connectors.base import BaseConnector


class WeGlideConnector(BaseConnector):
    def test_connection(self) -> bool:
        raise NotImplementedError('WeGlide connector not yet implemented')

    def fetch_flights(self, date_from: date, date_to: date) -> list[dict]:
        raise NotImplementedError('WeGlide connector not yet implemented')
