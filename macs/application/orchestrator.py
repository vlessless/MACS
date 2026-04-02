"""Orchestrator for managing Task lifecycles and state transitions."""

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from macs.domain.entities import PostMortemReport, Task, ThoughtLog
from macs.domain.enums import EventPriority, TaskStatus
from macs.domain.exceptions import MaxStrikesExceededError
from macs.domain.interfaces import InfrastructureManifest

# Type Alias for State Handlers
HandlerFunc = Callable[[Task], Awaitable[Task]]


class TaskOrchestrator:
    """The central 'Brain' of the system, managing state transitions.

    Reasoning:
        The Orchestrator coordinates between the state machine logic and
        external providers using an InfrastructureManifest to maintain
        Domain layer isolation.
    """

    def __init__(self, manifest: InfrastructureManifest) -> None:
        """Initializes the orchestrator with the infrastructure manifest.

        Args:
            manifest: A container holding the required interface implementations.
        """
        self._uow = manifest.uow
        self._queue = manifest.queue
        self._integration = manifest.integration
        self._container = manifest.container
        self._vcs = manifest.vcs

        # State transition dispatch table (Iterative logic, no recursion)
        self._dispatch_table: dict[TaskStatus, HandlerFunc] = {
            TaskStatus.PENDING: self._handle_pending,
            TaskStatus.IN_PROGRESS: self._handle_in_progress,
            TaskStatus.STALLED_FOR_HUMAN: self._handle_stalled,
        }

    async def process_task(self, task_id: UUID) -> None:
        """The core processing loop for a single task."""
        async with self._uow as uow:
            task: Task | None = await uow.tasks.get_task(task_id)

            if task is None:
                await self._integration.broadcast(
                    ThoughtLog(
                        agent="Orchestrator",
                        action="TASK_NOT_FOUND",
                        reason=f"Attempted to process non-existent task {task_id}",
                        priority=EventPriority.HIGH,
                    )
                )
                raise RuntimeError(f"Task {task_id} not found in repository.")

            try:
                handler: HandlerFunc | None = self._dispatch_table.get(task.status)

                if handler is None:
                    raise ValueError(
                        f"No handler registered for TaskStatus: {task.status.name}"
                    )

                updated_task: Task = await handler(task)

            except MaxStrikesExceededError as err:
                updated_task = await self._handle_circuit_breaker_failure(
                    task, str(err)
                )

            await uow.tasks.update_task(updated_task)
            await uow.commit()

    async def _handle_circuit_breaker_failure(self, task: Task, error_msg: str) -> Task:
        """Generates a post-mortem and halts the task after the 5th strike."""
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

        halt_log: dict[str, Any] = {
            "action": "HALT",
            "reason": "Max strikes exceeded",
            "status": "STALLED_FOR_HUMAN",
        }
        task.thought_trace.append(halt_log)

        await self._integration.broadcast(
            ThoughtLog(
                agent="QA_GATEKEEPER",
                action="INTERVENTION_REQUIRED",
                reason="5-Strike Circuit Breaker triggered. System Halted.",
                priority=EventPriority.CRITICAL,
                metadata={"task_id": str(task.id), "error": error_msg},
            )
        )

        return task

    async def _handle_stalled(self, task: Task) -> Task:
        """Terminal state handler for tasks requiring human intervention."""
        return task

    async def _handle_pending(self, task: Task) -> Task:
        """Transition logic for tasks in the PENDING state."""
        old_status = task.status.name
        task.status = TaskStatus.IN_PROGRESS

        task.thought_trace.append(
            {"action": "TRANSITION", "from": old_status, "to": "IN_PROGRESS"}
        )

        await self._integration.broadcast(
            ThoughtLog(
                agent="Orchestrator",
                action="TRANSITION",
                reason=f"Moving task from {old_status} to IN_PROGRESS",
                priority=EventPriority.LOW,
            )
        )
        return task

    async def _handle_in_progress(self, task: Task) -> Task:
        """Transition logic for tasks in the IN_PROGRESS state."""
        return task
