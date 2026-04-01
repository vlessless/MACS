"""SQLAlchemy models for MACS persistence layer."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from macs.domain.enums import TaskStatus


class Base(DeclarativeBase):
    """Base class for all infrastructure models."""

    pass


class TaskTable(Base):
    """Database representation of a MACS Task.

    Includes a GIN index on thought_trace for efficient searching of agent actions.
    """

    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    title: Mapped[str]
    description: Mapped[str]
    status: Mapped[TaskStatus]
    assigned_agent_id: Mapped[UUID | None]
    strike_count: Mapped[int] = mapped_column(default=0)
    thought_trace: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    post_mortem_report: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, default=None
    )

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    votes: Mapped[list["ConsensusVoteTable"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "ix_tasks_thought_trace_gin",
            "thought_trace",
            postgresql_using="gin",
        ),
    )


class ConsensusVoteTable(Base):
    """Database representation of a TL Consensus Vote."""

    __tablename__ = "consensus_votes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id"))
    agent_id: Mapped[UUID]
    vote: Mapped[bool]
    raw_rationale: Mapped[str]
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now())

    task: Mapped["TaskTable"] = relationship(back_populates="votes")
