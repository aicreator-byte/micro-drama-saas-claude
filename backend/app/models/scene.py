"""Scene and SceneCharacter models"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Enum as SQLEnum, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class SceneStatus(PyEnum):
    PLANNED = "planned"
    WRITING = "writing"
    PROMPTS_READY = "prompts_ready"
    ASSETS_GENERATING = "assets_generating"
    ASSETS_READY = "assets_ready"
    COMPLETED = "completed"


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    episode_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True)
    location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    scene_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str | None] = mapped_column(Text, nullable=True)
    camera_directions: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SceneStatus] = mapped_column(
        SQLEnum(SceneStatus), default=SceneStatus.PLANNED, nullable=False
    )
    estimated_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)  # seconds
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    episode: Mapped["Episode"] = relationship("Episode", back_populates="scenes")
    location: Mapped["Location | None"] = relationship("Location", back_populates="scenes")
    characters: Mapped[list["SceneCharacter"]] = relationship(
        "SceneCharacter", back_populates="scene", cascade="all, delete-orphan"
    )
    dialogues: Mapped[list["Dialogue"]] = relationship(
        "Dialogue", back_populates="scene", cascade="all, delete-orphan", order_by="Dialogue.order_index"
    )
    prompts: Mapped[list["Prompt"]] = relationship(
        "Prompt", back_populates="scene", cascade="all, delete-orphan"
    )
    assets: Mapped[list["Asset"]] = relationship(
        "Asset", back_populates="scene", cascade="all, delete-orphan"
    )
    flow_tasks: Mapped[list["FlowBridge"]] = relationship(
        "FlowBridge", back_populates="scene", cascade="all, delete-orphan"
    )
    story_generations: Mapped[list["StoryEngine"]] = relationship(
        "StoryEngine", back_populates="scene", cascade="all, delete-orphan"
    )
    shots: Mapped[list["Shot"]] = relationship(
        "Shot", back_populates="scene", cascade="all, delete-orphan", order_by="Shot.order_index"
    )
    scene_generations: Mapped[list["SceneEngine"]] = relationship(
        "SceneEngine", back_populates="scene", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_scenes_episode_number", "episode_id", "scene_number", unique=True),
        Index("ix_scenes_episode_status", "episode_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Scene(id={self.id}, episode={self.episode_id}, number={self.scene_number})>"


class SceneCharacter(Base):
    __tablename__ = "scene_characters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scene_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, index=True)
    character_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    role_in_scene: Mapped[str | None] = mapped_column(String(100), nullable=True)  # main, supporting, cameo
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    scene: Mapped["Scene"] = relationship("Scene", back_populates="characters")
    character: Mapped["Character"] = relationship("Character", back_populates="scene_links")

    __table_args__ = (
        UniqueConstraint("scene_id", "character_id", name="uq_scene_character"),
    )

    def __repr__(self) -> str:
        return f"<SceneCharacter(scene={self.scene_id}, character={self.character_id})>"