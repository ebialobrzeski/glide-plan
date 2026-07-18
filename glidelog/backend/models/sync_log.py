"""SyncLog model — records each synchronisation attempt."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class SyncLog(Base):
    __tablename__ = 'sync_log'

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
    connector_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('connectors.id', ondelete='SET NULL'),
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text('NOW()'),
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='running', server_default='running')
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    flights_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')

    connector: Mapped[Optional[object]] = relationship('Connector', back_populates='sync_logs')

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'connector_id': str(self.connector_id) if self.connector_id else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'status': self.status,
            'message': self.message,
            'flights_imported': self.flights_imported,
        }
