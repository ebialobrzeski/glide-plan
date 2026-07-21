"""User tier / quota helpers used by GlideLog's auth endpoints."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from backend.config import TIER_LIMITS
from backend.models.user import User


def get_tier_limits(tier: str) -> dict:
    return TIER_LIMITS.get(tier, TIER_LIMITS['free'])


def update_preferred_language(db: Session, user: User, lang_code: Optional[str]) -> None:
    """Set or clear a user's preferred UI language."""
    user.preferred_language = lang_code or None
    db.flush()
