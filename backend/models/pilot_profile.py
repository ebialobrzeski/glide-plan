"""PilotProfile — stores manually entered pilot data that cannot be derived from flight logs.

This is a 1-to-1 child table of users, keeping the users table slim.
All fields here require the pilot to enter them manually because they originate
from official documents (licenses, medical certificates, exam records) rather
than flight-log entries.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin


class PilotProfile(TimestampMixin, Base):
    __tablename__ = 'pilot_profiles'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,          # 1-to-1 relationship enforced at DB level
    )

    # ── Club / airfield ────────────────────────────────────────────────────
    club_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    home_airfield: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # ── SPL Licence ────────────────────────────────────────────────────────
    license_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    license_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True,
        doc='Date the SPL licence was first issued')

    # ── Medical certificate ────────────────────────────────────────────────
    # Class: 'LAPL' | 'Class 2' | 'Class 1' | other
    medical_class: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    medical_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True,
        doc='Expiry date of the medical certificate')
    medical_issue_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # ── Launch methods authorised by practical exam ────────────────────────
    # EASA SFCL.130: privileges restricted to launch methods passed in exam.
    # Stored as an array of codes: 'W' (winch), 'S' (aerotow), 'E' (self-launch/TMG).
    launch_methods_exam: Mapped[Optional[list]] = mapped_column(
        ARRAY(String), nullable=True,
        doc="Launch method codes passed in the practical exam e.g. ['W', 'S']"
    )

    # ── Skill test / proficiency check ────────────────────────────────────
    skill_test_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True,
        doc='Date of most recent skill test or proficiency check')
    skill_test_examiner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # ── Additional ratings / endorsements ─────────────────────────────────
    has_tmg: Mapped[bool] = mapped_column(Boolean, nullable=False,
        default=False, server_default='FALSE',
        doc='Touring Motor Glider (TMG) endorsement')
    tmg_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True,
        doc='Date the TMG endorsement was granted')

    has_aerobatics: Mapped[bool] = mapped_column(Boolean, nullable=False,
        default=False, server_default='FALSE')
    aerobatics_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    has_tow: Mapped[bool] = mapped_column(Boolean, nullable=False,
        default=False, server_default='FALSE',
        doc='Tow-plane or aerotow endorsement')
    tow_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # ── Passenger carriage thresholds (SFCL.115) ──────────────────────────
    # These can be partially inferred from flight data, but pilots may also
    # enter them manually for flights predating the logbook.
    pic_hours_pre_logbook: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        doc='PIC flight hours logged before this logbook system (minutes)'
    )
    pic_launches_pre_logbook: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        doc='PIC launches logged before this logbook system'
    )

    # ── Notes ─────────────────────────────────────────────────────────────
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Relationship back to user ──────────────────────────────────────────
    user: Mapped[Optional[object]] = relationship('User', back_populates='pilot_profile')

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'club_name': self.club_name,
            'home_airfield': self.home_airfield,
            'license_number': self.license_number,
            'license_date': self.license_date.isoformat() if self.license_date else None,
            'medical_class': self.medical_class,
            'medical_expiry': self.medical_expiry.isoformat() if self.medical_expiry else None,
            'medical_issue_date': self.medical_issue_date.isoformat() if self.medical_issue_date else None,
            'launch_methods_exam': self.launch_methods_exam or [],
            'skill_test_date': self.skill_test_date.isoformat() if self.skill_test_date else None,
            'skill_test_examiner': self.skill_test_examiner,
            'has_tmg': self.has_tmg,
            'tmg_date': self.tmg_date.isoformat() if self.tmg_date else None,
            'has_aerobatics': self.has_aerobatics,
            'aerobatics_date': self.aerobatics_date.isoformat() if self.aerobatics_date else None,
            'has_tow': self.has_tow,
            'tow_date': self.tow_date.isoformat() if self.tow_date else None,
            'pic_hours_pre_logbook': self.pic_hours_pre_logbook,
            'pic_launches_pre_logbook': self.pic_launches_pre_logbook,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
