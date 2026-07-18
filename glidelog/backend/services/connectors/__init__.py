"""Connector factory — returns the right BaseConnector implementation for a DB record."""
from backend.services.connectors.base import BaseConnector
from backend.services.connectors.echrono import EchronoConnector
from backend.services.connectors.leonardo import LeonardoConnector
from backend.services.connectors.weglide import WeGlideConnector
from backend.services.connectors.seeyou import SeeYouConnector


def get_connector(db_record) -> BaseConnector:
    """Return a connector instance for the given Connector DB record."""
    mapping = {
        'echrono': EchronoConnector,
        'leonardo': LeonardoConnector,
        'weglide': WeGlideConnector,
        'seeyou': SeeYouConnector,
    }
    cls = mapping.get(db_record.type)
    if cls is None:
        raise ValueError(f'Unknown connector type: {db_record.type}')
    return cls(db_record)


__all__ = ['get_connector', 'BaseConnector']
