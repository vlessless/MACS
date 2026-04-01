"""Orchestrator for managing Task lifecycles and state transitions."""

from collections.abc import Awaitable, Callable
from uuid import UUID

from macs.domain.entities import PostMortemReport, Task
from macs.domain.enums import TaskStatus
from macs.domain.exceptions import MaxStrikesExceededError
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

        # Ticket 1.2.2 & 1.2.3: Dispatch Table mapping Status to private handlers
        self._dispatch_table: dict[TaskStatus, HandlerFunc] = {
            TaskStatus.PENDING: self._handle_pending,
            TaskStatus.IN_PROGRESS: self._handle_in_progress,
            TaskStatus.STALLED_FOR_HUMAN: self._handle_stalled,
        }

    async def process_task(self, task_id: UUID) -> None:
        """The core processing loop for a single task.

        Args:
            task_id: The unique identifier of the task to be processed.

        Raises:
            ValueError: If the task status has no registered handler.
            RuntimeError: If the task is not found in the repository.

        Reasoning:
            Maintains the 'Single Persistence' rule. It wraps execution in a
            Circuit Breaker to catch domain-specific strike limits and trigger
            the Post-Mortem protocol.
        """
        task: Task | None = self._repo.get_task(task_id)

        if task is None:
            raise RuntimeError(f"Task {task_id} not found in repository.")

        try:
            # Dispatch based on state
            handler: HandlerFunc | None = self._dispatch_table.get(task.status)

            if handler is None:
                raise ValueError(
                    f"No handler registered for TaskStatus: {task.status.name}"
                )

            # Execute handler logic
            updated_task: Task = await handler(task)

        except MaxStrikesExceededError as err:
            # Ticket 1.2.3: Circuit Breaker triggered
            updated_task = self._handle_circuit_breaker_failure(task, str(err))

        # Persist the final state (Success or Failure)
        self._repo.update_task(updated_task)

    def _handle_circuit_breaker_failure(self, task: Task, error_msg: str) -> Task:
        """Generates a post-mortem and halts the task after the 5th strike.

        Args:
            task: The task that exceeded the strike limit.
            error_msg: The error message from the MaxStrikesExceededError.

        Returns:
            Task: The task updated with a PostMortemReport and STALLED status.

        Reasoning:
            This fulfills the "5-Strike Rule" requirements. It extracts context
            from the thought trace to provide human developers with a starting
            point for manual intervention.
        """
        # Extract last action from thought trace for context
        # Sentinel Check: Prevent IndexError if trace is empty
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
        """Terminal state handler for tasks requiring human intervention.

        Args:
            task: The stalled task entity.

        Returns:
            Task: The unmodified task entity (KISS - no-op).

        Reasoning:
            Ensures that if the orchestrator picks up a STALLED task,
            it does not perform any autonomous actions.
        """
        return task

    async def _handle_pending(self, task: Task) -> Task:
        """Transition logic for tasks in the PENDING state.

        Args:
            task: The task entity to be processed.

        Returns:
            Task: The mutated task entity with updated status.
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
        """
        return task
