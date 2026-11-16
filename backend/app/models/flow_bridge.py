"""Flow Bridge model for Google Flow integration"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class FlowTaskType(PyEnum):
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
    PROMPT_PREPARATION = "prompt_preparation"
    ASSET_ORGANIZATION = "asset_organization"


class FlowTaskStatus(PyEnum):
    PENDING = "pending"
    READY_FOR_FLOW = "ready_for_flow"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    IMPORTED = "imported"


class FlowBridge(Base):
    __tablename__ = "flow_bridge"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True, index=True)
    scene_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), nullable=True, index=True)
    google_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("google_accounts.id"), nullable=True)
    task_type: Mapped[FlowTaskType] = mapped_column(SQLEnum(FlowTaskType), nullable=False)
    status: Mapped[FlowTaskStatus] = mapped_column(SQLEnum(FlowTaskStatus), default=FlowTaskStatus.PENDING, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_prompts: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of prompts
    reference_assets: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of asset IDs
    flow_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)  # Deep link to Flow
    output_assets: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of generated asset IDs
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    project: Mapped["Project"] = relationship("Project", back_populates="flow_tasks")
    episode: Mapped["Episode | None"] = relationship("Episode", back_populates="flow_tasks")
    scene: Mapped["Scene | None"] = relationship("Scene", back_populates="flow_tasks")

    __table_args__ = (
        Index("ix_flow_bridge_project_status", "project_id", "status"),
        Index("ix_flow_bridge_episode_status", "episode_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<FlowBridge(id={self.id}, type={self.task_type}, status={self.status})>"