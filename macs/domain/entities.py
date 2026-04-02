"""Pure Domain Entities for the MACS ecosystem."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from .enums import AgentRole, EventPriority, TaskStatus
from .exceptions import MaxStrikesExceededError

# MACS System Constants
MAX_STRIKE_COUNT: int = 5


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


class ConsensusResult(BaseModel):
    """The aggregate outcome of a Hybrid Consensus evaluation."""

    is_approved: bool
    is_final: bool
    summary_rationale: str


class ExecutionResult(BaseModel):
    """The outcome of a command execution inside a Sibling Container."""

    model_config = ConfigDict(frozen=True)

    stdout: str
    stderr: str
    exit_code: int
    duration: float
    pytest_report: dict[str, Any] | None = None


class PostMortemReport(BaseModel):
    """A report generated after the 5th strike to assist human recovery."""

    hypothesis: str
    observed_error: str
    blocker: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ThoughtLog(BaseModel):
    """Standardized log structure for the MACS Thought Trace."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    agent: str
    action: str
    reason: str
    priority: EventPriority = EventPriority.LOW
    metadata: dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """The central entity tracking the SDLC progress of a specific requirement."""

    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent_id: UUID | None = None
    strike_count: int = Field(default=0, ge=0, le=MAX_STRIKE_COUNT)
    thought_trace: list[dict[str, Any]] = Field(default_factory=list)
    post_mortem_report: PostMortemReport | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def increment_strike(self) -> None:
        """Increments the strike count and updates the modified timestamp.

        Raises:
            MaxStrikesExceededError: If the strike count reaches the system limit.

        Reasoning:
            The 5-Strike Protocol requires a Hard Halt upon the 5th consecutive
            failure. By raising the exception when the count reaches the limit,
            we ensure the Orchestrator's circuit breaker logic is engaged
            before any further state transitions occur.
        """
        self.strike_count += 1
        self.updated_at = datetime.now(UTC)

        if self.strike_count >= MAX_STRIKE_COUNT:
            # Fixed line length for E501
            msg = f"Task {self.id} reached strike limit ({MAX_STRIKE_COUNT})."
            raise MaxStrikesExceededError(msg)

    def attach_post_mortem(self, report: PostMortemReport) -> None:
        """Links a post-mortem report to the task for human review."""
        self.post_mortem_report = report
        self.updated_at = datetime.now(UTC)

    def is_reviewable(self) -> bool:
        """Determines if the task is currently awaiting team lead approval."""
        return self.status == TaskStatus.TL_REVIEW
