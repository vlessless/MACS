"""Orchestrator for managing Task lifecycles and state transitions."""

from collections.abc import Awaitable, Callable
from uuid import UUID

from macs.domain.entities import Task
from macs.domain.enums import TaskStatus
from macs.domain.interfaces import IQueueProvider, IStateRepository

# Type Alias for State Handlers
HandlerFunc = Callable[[Task], Awaitable[Task]]


class TaskOrchestrator:
    """The central 'Brain' of the system, managing state transitions.

    This class coordinates the workflow of tasks by routing them to specific
    handlers based on their current status using a Dispatch Table.
    """

    def __init__(
        self,
        repository: IStateRepository,
        queue: IQueueProvider,
    ) -> None:
        """Initializes the orchestrator with domain-defined interfaces.

        Args:
            repository: Persistence interface for task and agent state.
            queue: Interface for task enqueuing and retrieval.

        Reasoning:
            Constructor injection of interfaces (Dependency Inversion) ensures
            the orchestrator remains agnostic of the underlying DB or Queue tech.
        """
        self._repo = repository
        self._queue = queue

        # Ticket 1.2.2: Dispatch Table mapping Status to private handlers
        self._dispatch_table: dict[TaskStatus, HandlerFunc] = {
            TaskStatus.PENDING: self._handle_pending,
            TaskStatus.IN_PROGRESS: self._handle_in_progress,
            # Additional statuses will be mapped here as logic is expanded.
        }

    async def process_task(self, task_id: UUID) -> None:
        """The core processing loop for a single task.

        Args:
            task_id: The unique identifier of the task to be processed.

        Raises:
            ValueError: If the task status has no registered handler.
            RuntimeError: If the task is not found in the repository.

        Reasoning:
            Maintains the 'Single Persistence' rule: handlers mutate the object,
            and the orchestrator saves the final state once at the end.
        """
        task: Task | None = self._repo.get_task(task_id)

        if task is None:
            raise RuntimeError(f"Task {task_id} not found in repository.")

        # Dispatch based on state
        handler: HandlerFunc | None = self._dispatch_table.get(task.status)

        if handler is None:
            raise ValueError(
                f"No handler registered for TaskStatus: {task.status.name}"
            )

        # Execute handler logic
        updated_task: Task = await handler(task)

        # Persist the final state
        self._repo.update_task(updated_task)

    async def _handle_pending(self, task: Task) -> Task:
        """Transition logic for tasks in the PENDING state.

        Args:
            task: The task entity to be processed.

        Returns:
            Task: The mutated task entity with updated status.

        Reasoning:
            Placeholder for logic that assigns agents and initiates work.
        """
        task.status = TaskStatus.IN_PROGRESS
        task.thought_trace.append(
            {"action": "TRANSITION", "from": "PENDING", "to": "IN_PROGRESS"}
        )
        return task

    async def _handle_in_progress(self, task: Task) -> Task:
        """Transition logic for tasks in the IN_PROGRESS state.

        Args:
            task: The task entity to be processed.

        Returns:
            Task: The mutated task entity.

        Reasoning:
            Placeholder for logic that routes the task to specific developer agents.
        """
        # Logic to be implemented in subsequent tickets (e.g., Code Generation)
        return task
