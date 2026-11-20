"""Revoked JWTs (future-dev round 2, token revocation).

JWTs are stateless, so "logout" needs a server-side denylist: when a
token is revoked its jti (unique token id, added to every token issued
since round 2) is stored here until the token's own expiry, and
`get_current_user_id` / `/auth/refresh` reject it. Rows past expiry
are deleted opportunistically by `revoke_token()`.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    token_type: Mapped[str] = mapped_column(String(20), nullable=False)  # access | refresh
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<RevokedToken(jti={self.jti}, type={self.token_type})>"
