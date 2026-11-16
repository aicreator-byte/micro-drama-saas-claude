"""Prompt model"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class PromptType(PyEnum):
    CHARACTER_IMAGE = "character_image"
    LOCATION_IMAGE = "location_image"
    SCENE_IMAGE = "scene_image"
    VIDEO_GENERATION = "video_generation"
    CAMERA_MOVEMENT = "camera_movement"
    CHARACTER_ACTION = "character_action"
    DIALOGUE_AUDIO = "dialogue_audio"
    BACKGROUND_MUSIC = "background_music"
    SOUND_EFFECT = "sound_effect"
    SUBTITLE = "subtitle"


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True, index=True)
    scene_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), nullable=True, index=True)
    character_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), nullable=True, index=True)
    location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"), nullable=True, index=True)
    prompt_type: Mapped[PromptType] = mapped_column(SQLEnum(PromptType), nullable=False, index=True)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    parameters: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: model, steps, cfg, etc.
    generated_result: Mapped[str | None] = mapped_column(Text, nullable=True)  # URL or base64
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, generating, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    project: Mapped["Project"] = relationship("Project", back_populates="prompts")
    episode: Mapped["Episode | None"] = relationship("Episode", back_populates="prompts")
    scene: Mapped["Scene | None"] = relationship("Scene", back_populates="prompts")
    character: Mapped["Character | None"] = relationship("Character")
    location: Mapped["Location | None"] = relationship("Location")

    __table_args__ = (
        Index("ix_prompts_project_type", "project_id", "prompt_type"),
        Index("ix_prompts_scene_type", "scene_id", "prompt_type"),
    )

    def __repr__(self) -> str:
        return f"<Prompt(id={self.id}, type={self.prompt_type}, status={self.status})>"