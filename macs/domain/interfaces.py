"""Abstract Base Classes for the MACS Domain Layer."""

from abc import ABC, abstractmethod
from collections.abc import Generator
from uuid import UUID

from .entities import Agent, ConsensusVote, Task


class IStateRepository(ABC):
    """Interface for persistent storage of the system state.

    Follows Dependency Inversion: Domain does not know about storage tech.
    """

    @abstractmethod
    def get_task(self, task_id: UUID) -> Task | None:
        """Retrieves a task by its unique identifier."""
        pass

    @abstractmethod
    def update_task(self, task: Task) -> None:
        """Persists the updated state of an existing task."""
        pass

    @abstractmethod
    def save_agent(self, agent: Agent) -> None:
        """Registers or updates an agent in the system state."""
        pass

    @abstractmethod
    def add_vote(self, task_id: UUID, vote: ConsensusVote) -> None:
        """Appends a Team Lead vote to a task's consensus record."""
        pass

    @abstractmethod
    def stream_active_tasks(self) -> Generator[Task, None, None]:
        """Yields tasks currently in progress to maintain low memory overhead.

        Yields:
            Task: The next active task in the sequence.
        """
        pass


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
