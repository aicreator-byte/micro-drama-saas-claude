"""Asset model"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class AssetType(PyEnum):
    CHARACTER_IMAGE = "character_image"
    LOCATION_IMAGE = "location_image"
    SCENE_IMAGE = "scene_image"
    VIDEO_CLIP = "video_clip"
    AUDIO_CLIP = "audio_clip"
    BACKGROUND_MUSIC = "background_music"
    SOUND_EFFECT = "sound_effect"
    SUBTITLE_FILE = "subtitle_file"
    FINAL_EPISODE = "final_episode"
    THUMBNAIL = "thumbnail"
    REFERENCE = "reference"


class AssetStatus(PyEnum):
    PENDING = "pending"
    UPLOADING = "uploading"
    READY = "ready"
    FAILED = "failed"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True, index=True)
    scene_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), nullable=True, index=True)
    prompt_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("prompts.id", ondelete="SET NULL"), nullable=True)
    asset_type: Mapped[AssetType] = mapped_column(SQLEnum(AssetType), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)  # S3 key or local path
    file_size: Mapped[int | None] = mapped_column(nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration: Mapped[float | None] = mapped_column(nullable=True)  # for video/audio
    width: Mapped[int | None] = mapped_column(nullable=True)
    height: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[AssetStatus] = mapped_column(SQLEnum(AssetStatus), default=AssetStatus.PENDING, nullable=False)
    asset_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON for extra data
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
    project: Mapped["Project"] = relationship("Project", back_populates="assets")
    episode: Mapped["Episode | None"] = relationship("Episode", back_populates="assets")
    scene: Mapped["Scene | None"] = relationship("Scene", back_populates="assets")

    __table_args__ = (
        Index("ix_assets_project_type", "project_id", "asset_type"),
        Index("ix_assets_episode_type", "episode_id", "asset_type"),
        Index("ix_assets_scene_type", "scene_id", "asset_type"),
    )

    def __repr__(self) -> str:
        return f"<Asset(id={self.id}, type={self.asset_type}, file={self.file_name})>"