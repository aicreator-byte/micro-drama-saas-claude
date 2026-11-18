"""App Settings model for configurable AI providers and OAuth credentials"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.core.security import encrypt_data, decrypt_data


class AppSettings(Base):
    __tablename__ = "app_settings"

    # Singleton pattern - only one row with id=1
    id: Mapped[int] = mapped_column(primary_key=True, default=1)

    # AI Providers configuration (JSON array of provider objects)
    # Each: {id, provider, model, key_env, enabled, priority}
    ai_providers: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    # Google OAuth credentials (encrypted)
    google_oauth_client_id_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_oauth_client_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AppSettings(id={self.id})>"

    # Helper methods for encrypted fields
    def set_google_oauth_client_id(self, value: str) -> None:
        self.google_oauth_client_id_encrypted = encrypt_data(value)

    def get_google_oauth_client_id(self) -> str | None:
        if self.google_oauth_client_id_encrypted:
            return decrypt_data(self.google_oauth_client_id_encrypted)
        return None

    def set_google_oauth_client_secret(self, value: str) -> None:
        self.google_oauth_client_secret_encrypted = encrypt_data(value)

    def get_google_oauth_client_secret(self) -> str | None:
        if self.google_oauth_client_secret_encrypted:
            return decrypt_data(self.google_oauth_client_secret_encrypted)
        return None

    def has_google_oauth_configured(self) -> bool:
        return bool(self.google_oauth_client_id_encrypted and self.google_oauth_client_secret_encrypted)