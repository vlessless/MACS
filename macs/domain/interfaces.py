"""Abstract Base Classes for the MACS Domain Layer."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Self
from uuid import UUID

from .entities import (
    Agent,
    ConsensusResult,
    ConsensusVote,
    ExecutionResult,
    Task,
    ThoughtLog,
)


@dataclass(frozen=True)
class InfrastructureManifest:
    """A container for infrastructure dependencies.

    Reasoning:
        Groups the core providers into a single object to prevent
        constructor bloat and satisfy Pylint/Ruff argument limits.
    """

    uow: "IUnitOfWork"
    queue: "IQueueProvider"
    integration: "IIntegrationProvider"
    container: "IContainerProvider"
    vcs: "IVersionControlProvider"
    consensus: "IConsensusService"


class ISystemSettings(ABC):
    """Interface for system-wide configuration management."""

    @abstractmethod
    def get_database_url(self) -> str:
        """Returns the PostgreSQL connection string."""
        pass

    @abstractmethod
    def get_redis_url(self) -> str:
        """Returns the Redis connection string."""
        pass

    @abstractmethod
    def get_docker_base_image(self) -> str:
        """Returns the default Docker image for sibling containers."""
        pass

    @abstractmethod
    def get_log_level(self) -> str:
        """Returns the configured logging level (e.g., INFO, DEBUG).."""
        pass


class IStateRepository(ABC):
    """Interface for persistent storage of the system state."""

    @abstractmethod
    async def get_task(self, task_id: UUID) -> Task | None:
        """Retrieves a task by its unique identifier."""
        pass

    @abstractmethod
    async def update_task(self, task: Task) -> None:
        """Persists the updated state of an existing task."""
        pass

    @abstractmethod
    async def save_agent(self, agent: Agent) -> None:
        """Registers or updates an agent in the system state."""
        pass

    @abstractmethod
    async def add_vote(self, task_id: UUID, vote: ConsensusVote) -> None:
        """Appends a Team Lead vote to a task's consensus record."""
        pass

    @abstractmethod
    async def get_votes(self, task_id: UUID) -> list[ConsensusVote]:
        """Retrieves all votes associated with a specific task.

        Args:
            task_id: The UUID of the task.

        Returns:
            list[ConsensusVote]: A list of domain vote entities.
        """
        pass

    @abstractmethod
    async def stream_active_tasks(self) -> AsyncGenerator[Task, None]:
        """Yields tasks in progress via an async generator."""
        yield  # type: ignore


class IQueueProvider(ABC):
    """Interface for the Task Queueing system (e.g., Redis)."""

    @abstractmethod
    def push_task(self, task_id: UUID) -> None:
        """Enqueues a task for agent processing."""
        pass

    @abstractmethod
    def pop_task(self) -> UUID | None:
        """Retrieves the next available task ID from the queue."""
        pass

    @abstractmethod
    def get_queue_length(self) -> int:
        """Returns the number of pending tasks in the queue."""
        pass


class IUnitOfWork(ABC):
    """Interface for managing atomic database transactions."""

    tasks: IStateRepository

    @abstractmethod
    async def __aenter__(self) -> Self:
        """Starts the atomic transaction context."""
        pass

    @abstractmethod
    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        """Ends the context, ensuring rollback on failure."""
        pass

    @abstractmethod
    async def commit(self) -> None:
        """Commits all changes within the current transaction."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Aborts all changes within the current transaction."""
        pass


class IContainerProvider(ABC):
    """Interface for Sibling Container execution management."""

    @abstractmethod
    async def run_task(self, task_id: UUID, command: list[str]) -> ExecutionResult:
        """Executes a command within a dedicated sibling container."""
        pass


class IVersionControlProvider(ABC):
    """Interface for managing the Git "Stash & Sync" protocol."""

    @abstractmethod
    async def create_checkpoint(self, task_id: UUID) -> str:
        """Saves current work and cuts a human-fix-checkpoint branch."""
        pass

    @abstractmethod
    async def sync_checkpoint(self, task_id: UUID) -> None:
        """Resumes work from a checkpoint."""
        pass

    @abstractmethod
    async def get_diff(self, base_branch: str, head_branch: str) -> str:
        """Generates a diff between branches."""
        pass


class IIntegrationProvider(ABC):
    """Interface for the Integration Agent's real-time observability bridge."""

    @abstractmethod
    async def broadcast(self, log: ThoughtLog) -> None:
        """Sends a structured log message to all connected observers."""
        pass


class IConsensusService(ABC):
    """Interface for the Hybrid Consensus engine.

    Reasoning:
        Separates the logic of determining code quality and consensus
        from the orchestrator's state transition management.
    """

    @abstractmethod
    def evaluate_consensus(
        self, task: Task, votes: list[ConsensusVote]
    ) -> ConsensusResult:
        """Analyzes team lead votes to determine if a task is approved or rejected.

        Args:
            task: The Task entity being reviewed.
            votes: A list of votes cast by team leads.

        Returns:
            ConsensusResult: The decision and summary of the review process.
        """
        pass
