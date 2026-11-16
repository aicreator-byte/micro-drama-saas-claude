"""Series Bible model"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class SeriesBible(Base):
    __tablename__ = "series_bibles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    premise: Mapped[str | None] = mapped_column(Text, nullable=True)
    main_plot: Mapped[str | None] = mapped_column(Text, nullable=True)
    subplots: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    character_relationships: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    world_settings: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone_and_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    ending_direction: Mapped[str | None] = mapped_column(Text, nullable=True)
    episode_structure: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
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
    project: Mapped["Project"] = relationship("Project", back_populates="series_bible")

    def __repr__(self) -> str:
        return f"<SeriesBible(project_id={self.project_id})>"