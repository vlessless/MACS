"""Orchestrator for managing Task lifecycles and state transitions."""

from collections.abc import Awaitable, Callable
from uuid import UUID

from macs.domain.entities import PostMortemReport, Task
from macs.domain.enums import TaskStatus
from macs.domain.exceptions import MaxStrikesExceededError
from macs.domain.interfaces import IQueueProvider, IUnitOfWork

# Type Alias for State Handlers
HandlerFunc = Callable[[Task], Awaitable[Task]]


class TaskOrchestrator:
    """The central 'Brain' of the system, managing state transitions.

    Uses a Unit of Work to ensure atomicity of state and log updates.
    """

    def __init__(
        self,
        uow: IUnitOfWork,
        queue: IQueueProvider,
    ) -> None:
        """Initializes the orchestrator with domain-defined interfaces.

        Args:
            uow: Atomic Unit of Work for state persistence.
            queue: Interface for task enqueuing and retrieval.
        """
        self._uow = uow
        self._queue = queue

        self._dispatch_table: dict[TaskStatus, HandlerFunc] = {
            TaskStatus.PENDING: self._handle_pending,
            TaskStatus.IN_PROGRESS: self._handle_in_progress,
            TaskStatus.STALLED_FOR_HUMAN: self._handle_stalled,
        }

    async def process_task(self, task_id: UUID) -> None:
        """The core processing loop for a single task using atomic transactions.

        Args:
            task_id: The unique identifier of the task to be processed.

        Raises:
            ValueError: If the task status has no registered handler.
            RuntimeError: If the task is not found in the repository.

        Reasoning:
            All state transitions and thought trace updates are performed
            inside an async context manager to ensure partial failures
            do not leave the system in an inconsistent state.
        """
        async with self._uow as uow:
            task: Task | None = await uow.tasks.get_task(task_id)

            if task is None:
                raise RuntimeError(f"Task {task_id} not found in repository.")

            try:
                handler: HandlerFunc | None = self._dispatch_table.get(task.status)

                if handler is None:
                    raise ValueError(
                        f"No handler registered for TaskStatus: {task.status.name}"
                    )

                updated_task: Task = await handler(task)

            except MaxStrikesExceededError as err:
                updated_task = self._handle_circuit_breaker_failure(task, str(err))

            await uow.tasks.update_task(updated_task)
            await uow.commit()

    def _handle_circuit_breaker_failure(self, task: Task, error_msg: str) -> Task:
        """Generates a post-mortem and halts the task after the 5th strike.

        Args:
            task: The task that exceeded the strike limit.
            error_msg: The error message from the strike failure.

        Returns:
            Task: The task updated with a PostMortemReport and STALLED status.
        """
        last_action: str = "Initial Assignment"
        if task.thought_trace:
            last_action = str(task.thought_trace[-1].get("action", "Unknown Action"))

        report = PostMortemReport(
            hypothesis="Autonomous recovery exhausted 5 attempts without resolution.",
            observed_error=error_msg,
            blocker=f"Failed during action: {last_action}",
        )

        task.attach_post_mortem(report)
        task.status = TaskStatus.STALLED_FOR_HUMAN

        task.thought_trace.append(
            {
                "action": "HALT",
                "reason": "Max strikes exceeded",
                "status": "STALLED_FOR_HUMAN",
            }
        )

        return task

    async def _handle_stalled(self, task: Task) -> Task:
        """Terminal state handler for tasks requiring human intervention."""
        return task

    async def _handle_pending(self, task: Task) -> Task:
        """Transition logic for tasks in the PENDING state."""
        task.status = TaskStatus.IN_PROGRESS
        task.thought_trace.append(
            {"action": "TRANSITION", "from": "PENDING", "to": "IN_PROGRESS"}
        )
        return task

    async def _handle_in_progress(self, task: Task) -> Task:
        """Transition logic for tasks in the IN_PROGRESS state."""
        return task
