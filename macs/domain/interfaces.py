"""Abstract Base Classes for the MACS Domain Layer."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Self
from uuid import UUID

from .entities import Agent, ConsensusVote, Task


class IStateRepository(ABC):
    """Interface for persistent storage of the system state.

    Follows Dependency Inversion: Domain does not know about storage tech.
    Methods are asynchronous to support non-blocking orchestration logic.
    """

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
    async def stream_active_tasks(self) -> AsyncGenerator[Task, None]:
        """Yields tasks in progress via an async generator for memory efficiency.

        Yields:
            Task: The next active task in the sequence.
        """
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
    """Interface for managing atomic database transactions.

    Encapsulates multiple repository actions into a single commit/rollback cycle.
    """

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
