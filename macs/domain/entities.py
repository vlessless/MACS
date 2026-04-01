"""Pure Domain Entities for the MACS ecosystem."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from .enums import AgentRole, TaskStatus


class Agent(BaseModel):
    """Represents an autonomous worker or supervisor within the system."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    name: str
    role: AgentRole
    is_active: bool = True


class ConsensusVote(BaseModel):
    """A single vote cast by a Team Lead during the Hybrid Consensus phase."""

    agent_id: UUID
    vote: bool
    raw_rationale: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExecutionResult(BaseModel):
    """The outcome of a command execution inside a Sibling Container."""

    stdout: str
    stderr: str
    exit_code: int
    pytest_report: dict[str, Any] | None = None


class PostMortemReport(BaseModel):
    """A report generated after the 5th strike to assist human recovery."""

    hypothesis: str
    observed_error: str
    blocker: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Task(BaseModel):
    """The central entity tracking the SDLC progress of a specific requirement.

    Attributes:
        strike_count: Tracks consecutive pytest failures (5-Strike Rule).
        thought_trace: A chronological log of agent reasoning and actions.
    """

    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent_id: UUID | None = None
    strike_count: int = Field(default=0, ge=0, le=5)
    thought_trace: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def increment_strike(self) -> None:
        """Increments the strike count and updates the modified timestamp."""
        self.strike_count += 1
        self.updated_at = datetime.now(UTC)
