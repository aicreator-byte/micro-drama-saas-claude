"""Story Engine model for AI story generation tracking"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class StoryGenerationType(PyEnum):
    STORY_IDEA = "story_idea"
    EPISODE_OUTLINE = "episode_outline"
    FULL_SERIES = "full_series"
    SCENE_BREAKDOWN = "scene_breakdown"
    DIALOGUE_GENERATION = "dialogue_generation"
    CHARACTER_DEVELOPMENT = "character_development"
    CONFLICT_DEVELOPMENT = "conflict_development"
    CLIFFHANGER = "cliffhanger"


class StoryGenerationStatus(PyEnum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class StoryEngine(Base):
    __tablename__ = "story_engine"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True, index=True)
    scene_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), nullable=True, index=True)
    generation_type: Mapped[StoryGenerationType] = mapped_column(SQLEnum(StoryGenerationType), nullable=False)
    status: Mapped[StoryGenerationStatus] = mapped_column(SQLEnum(StoryGenerationStatus), default=StoryGenerationStatus.PENDING, nullable=False)
    input_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_context: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON with context
    generated_output: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON structured output
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(nullable=True)
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
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="story_generations")
    episode: Mapped["Episode | None"] = relationship("Episode", back_populates="story_generations")
    scene: Mapped["Scene | None"] = relationship("Scene", back_populates="story_generations")

    __table_args__ = (
        Index("ix_story_engine_project_type", "project_id", "generation_type"),
        Index("ix_story_engine_episode_type", "episode_id", "generation_type"),
    )

    def __repr__(self) -> str:
        return f"<StoryEngine(id={self.id}, type={self.generation_type}, status={self.status})>"