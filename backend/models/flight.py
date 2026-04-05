"""Flight model — individual flight log entry."""
from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Time, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin


class Flight(TimestampMixin, Base):
    __tablename__ = 'flights'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
    )
    external_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    aircraft_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    aircraft_reg: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    pilot: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    instructor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    task: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    launch_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    takeoff_airport: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    takeoff_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    landing_airport: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    landing_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    flight_time_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    landings: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_instructor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='FALSE')
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default='echrono', server_default='echrono')
    connector_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('connectors.id', ondelete='SET NULL'),
        nullable=True,
    )
    import_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('import_log.id', ondelete='SET NULL'),
        nullable=True,
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text('NOW()'),
    )

    connector: Mapped[Optional[object]] = relationship('Connector', back_populates='flights')

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'external_id': self.external_id,
            'user_id': str(self.user_id),
            'date': self.date.isoformat() if self.date else None,
            'aircraft_type': self.aircraft_type,
            'aircraft_reg': self.aircraft_reg,
            'pilot': self.pilot,
            'instructor': self.instructor,
            'task': self.task,
            'launch_type': self.launch_type,
            'takeoff_airport': self.takeoff_airport,
            'takeoff_time': self.takeoff_time.strftime('%H:%M') if self.takeoff_time else None,
            'landing_airport': self.landing_airport,
            'landing_time': self.landing_time.strftime('%H:%M') if self.landing_time else None,
            'flight_time_min': self.flight_time_min,
            'landings': self.landings,
            'is_instructor': self.is_instructor,
            'price': float(self.price) if self.price is not None else None,
            'source': self.source,
            'connector_id': str(self.connector_id) if self.connector_id else None,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
