"""Episode model"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class EpisodeStatus(PyEnum):
    PLANNED = "planned"
    WRITING = "writing"
    SCENES_DONE = "scenes_done"
    PROMPTS_READY = "prompts_ready"
    ASSETS_GENERATING = "assets_generating"
    ASSETS_READY = "assets_ready"
    EDITING = "editing"
    COMPLETED = "completed"


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    synopsis: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[EpisodeStatus] = mapped_column(
        SQLEnum(EpisodeStatus), default=EpisodeStatus.PLANNED, nullable=False
    )
    estimated_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)  # seconds
    actual_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    production_cost: Mapped[float | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    project: Mapped["Project"] = relationship("Project", back_populates="episodes")
    scenes: Mapped[list["Scene"]] = relationship(
        "Scene", back_populates="episode", cascade="all, delete-orphan", order_by="Scene.scene_number"
    )
    prompts: Mapped[list["Prompt"]] = relationship(
        "Prompt", back_populates="episode", cascade="all, delete-orphan"
    )
    assets: Mapped[list["Asset"]] = relationship(
        "Asset", back_populates="episode", cascade="all, delete-orphan"
    )
    flow_tasks: Mapped[list["FlowBridge"]] = relationship(
        "FlowBridge", back_populates="episode", cascade="all, delete-orphan"
    )
    story_generations: Mapped[list["StoryEngine"]] = relationship(
        "StoryEngine", back_populates="episode", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_episodes_project_number", "project_id", "episode_number", unique=True),
        Index("ix_episodes_project_status", "project_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Episode(id={self.id}, number={self.episode_number}, status={self.status})>"