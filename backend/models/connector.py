"""Connector model — stores credentials and config for external flight data sources."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin


class Connector(TimestampMixin, Base):
    __tablename__ = 'connectors'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    login_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    password_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default='TRUE')
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    flights: Mapped[list] = relationship('Flight', back_populates='connector', passive_deletes=True)
    sync_logs: Mapped[list] = relationship('SyncLog', back_populates='connector', passive_deletes=True)

    def to_dict(self, include_credentials: bool = False) -> dict:
        d = {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'type': self.type,
            'display_name': self.display_name,
            'base_url': self.base_url,
            'config': self.config,
            'is_active': self.is_active,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'last_sync_status': self.last_sync_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_credentials:
            d['has_login'] = bool(self.login_encrypted)
            d['has_password'] = bool(self.password_encrypted)
        return d
