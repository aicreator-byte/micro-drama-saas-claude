"""Dialogue model"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Dialogue(Base):
    __tablename__ = "dialogues"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scene_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, index=True)
    character_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    dialogue_text: Mapped[str] = mapped_column(Text, nullable=False)
    parenthetical: Mapped[str | None] = mapped_column(Text, nullable=True)  # (whispering), (angry), etc.
    audio_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)  # For TTS generation
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    scene: Mapped["Scene"] = relationship("Scene", back_populates="dialogues")
    character: Mapped["Character"] = relationship("Character", back_populates="dialogues")

    __table_args__ = (
        Index("ix_dialogues_scene_order", "scene_id", "order_index"),
    )

    def __repr__(self) -> str:
        return f"<Dialogue(id={self.id}, scene={self.scene_id}, character={self.character_id})>"