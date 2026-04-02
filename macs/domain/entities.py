"""Pure Domain Entities for the MACS ecosystem."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from .enums import AgentRole, TaskStatus
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


class ExecutionResult(BaseModel):
    """The outcome of a command execution inside a Sibling Container.

    Attributes:
        stdout: Standard output from the container process.
        stderr: Standard error from the container process.
        exit_code: Process return code (0 for success).
        duration: Time taken in seconds for execution.
        pytest_report: Optional parsed JSON results from a test run.
    """

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


class Task(BaseModel):
    """The central entity tracking the SDLC progress of a specific requirement.

    Attributes:
        strike_count: Tracks consecutive pytest failures (Max 5).
        thought_trace: A chronological log of agent reasoning and actions.
        post_mortem_report: Detailed failure analysis for human intervention.
    """

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
            MaxStrikesExceededError: If the increment would exceed the limit.

        Reasoning:
            Enforces the 5-Strike Rule invariant at the domain level.
        """
        if self.strike_count >= MAX_STRIKE_COUNT:
            raise MaxStrikesExceededError(
                f"Task {self.id} has exceeded the maximum "
                f"strike limit ({MAX_STRIKE_COUNT})."
            )

        self.strike_count += 1
        self.updated_at = datetime.now(UTC)

    def attach_post_mortem(self, report: PostMortemReport) -> None:
        """Links a post-mortem report to the task for human review.

        Args:
            report: The generated failure analysis report.
        """
        self.post_mortem_report = report
        self.updated_at = datetime.now(UTC)
