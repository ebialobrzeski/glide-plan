"""ImportLog model — records each file import operation."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class ImportLog(Base):
    __tablename__ = 'import_log'

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
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text('NOW()'),
    )
    flights_new: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')
    flights_dup: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')
    flights_error: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='success', server_default='success')
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'source_type': self.source_type,
            'filename': self.filename,
            'imported_at': self.imported_at.isoformat() if self.imported_at else None,
            'flights_new': self.flights_new,
            'flights_dup': self.flights_dup,
            'flights_error': self.flights_error,
            'status': self.status,
            'message': self.message,
        }
