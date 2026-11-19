"""Auto-generate job models (Fase 1).

One job = 5 sequential steps (series_bible -> characters -> locations ->
episodes -> prompts). A failed step stops the pipeline; retry re-runs from
the failed step only. Re-running a job skips rows that already exist
(idempotent: no duplicate characters / locations / episodes).
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class AutoGenerateJobStatus(PyEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AutoGenerateStepName(PyEnum):
    SERIES_BIBLE = "series_bible"
    CHARACTERS = "characters"
    LOCATIONS = "locations"
    EPISODES = "episodes"
    PROMPTS = "prompts"


STEP_ORDER = [
    AutoGenerateStepName.SERIES_BIBLE,
    AutoGenerateStepName.CHARACTERS,
    AutoGenerateStepName.LOCATIONS,
    AutoGenerateStepName.EPISODES,
    AutoGenerateStepName.PROMPTS,
]


class AutoGenerateStepStatus(PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AutoGenerateJob(Base):
    __tablename__ = "auto_generate_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    genre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    total_episodes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    premise: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AutoGenerateJobStatus] = mapped_column(
        SQLEnum(AutoGenerateJobStatus), default=AutoGenerateJobStatus.RUNNING, nullable=False
    )
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

    steps: Mapped[list["AutoGenerateStep"]] = relationship(
        "AutoGenerateStep", back_populates="job", cascade="all, delete-orphan"
    )
    project: Mapped["Project"] = relationship("Project")

    def __repr__(self) -> str:
        return f"<AutoGenerateJob(id={self.id}, project_id={self.project_id}, status={self.status})>"


class AutoGenerateStep(Base):
    __tablename__ = "auto_generate_steps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auto_generate_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    step: Mapped[AutoGenerateStepName] = mapped_column(SQLEnum(AutoGenerateStepName), nullable=False)
    status: Mapped[AutoGenerateStepStatus] = mapped_column(
        SQLEnum(AutoGenerateStepStatus), default=AutoGenerateStepStatus.PENDING, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
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

    job: Mapped["AutoGenerateJob"] = relationship("AutoGenerateJob", back_populates="steps")

    __table_args__ = (
        Index("ix_auto_generate_steps_job_position", "job_id", "position"),
    )

    def __repr__(self) -> str:
        return f"<AutoGenerateStep(job_id={self.job_id}, step={self.step}, status={self.status})>"
