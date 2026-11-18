"""OAuth state model — server-side, single-use, TTL-bound.

Replaces the previous in-memory ``_oauth_states`` dict in
``app/api/google_accounts.py`` (audit F-M6/P1-19): the dict was lost on
every restart and did not work with more than one worker. States live
in the DB with a 10-minute expiry and are deleted on use. The
``redirect_uri`` used at /oauth/start is stored alongside the state so
the callback exchanges the code with exactly the same URI.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class OAuthState(Base):
    __tablename__ = "oauth_states"

    state: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    redirect_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_oauth_states_expires_at", "expires_at"),)

    def __repr__(self) -> str:
        return f"<OAuthState(user_id={self.user_id}, expires_at={self.expires_at})>"
