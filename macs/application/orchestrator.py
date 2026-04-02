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
        self._consensus = manifest.consensus

        # State transition dispatch table (Iterative logic, no recursion)
        self._dispatch_table: dict[TaskStatus, HandlerFunc] = {
            TaskStatus.PENDING: self._handle_pending,
            TaskStatus.IN_PROGRESS: self._handle_in_progress,
            TaskStatus.TL_REVIEW: self._handle_tl_review,
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

    async def _handle_tl_review(self, task: Task) -> Task:
        """Processes Hybrid Consensus votes and determines code approval.

        Args:
            task: The Task entity currently in TL_REVIEW.

        Returns:
            Task: The task with updated status and thought trace.

        Raises:
            MaxStrikesExceededError: Triggered if consensus rejection causes
                the strike count to exceed the limit.
        """
        votes = await self._uow.tasks.get_votes(task.id)
        result = self._consensus.evaluate_consensus(task, votes)

        if not result.is_final:
            await self._integration.broadcast(
                ThoughtLog(
                    agent="Orchestrator",
                    action="CONSENSUS_PENDING",
                    reason="Awaiting further Team Lead votes.",
                    priority=EventPriority.LOW,
                    metadata={"task_id": str(task.id), "vote_count": len(votes)},
                )
            )
            return task

        if result.is_approved:
            task.status = TaskStatus.COMPLETED
            action_desc = "CONSENSUS_APPROVED"
        else:
            # Rejection: Increment strike and cycle back to IN_PROGRESS
            # increment_strike() will raise MaxStrikesExceededError if limit hit.
            task.increment_strike()
            task.status = TaskStatus.IN_PROGRESS
            action_desc = "CONSENSUS_REJECTED"

        # Log to Thought Trace and broadcast
        consensus_log: dict[str, Any] = {
            "action": action_desc,
            "rationale": result.summary_rationale,
            "new_status": task.status.value,
            "strike_count": task.strike_count,
        }
        task.thought_trace.append(consensus_log)

        await self._integration.broadcast(
            ThoughtLog(
                agent="ConsensusService",
                action=action_desc,
                reason=result.summary_rationale,
                priority=EventPriority.MEDIUM,
                metadata={
                    "task_id": str(task.id),
                    "new_status": task.status.value,
                    "strike_count": task.strike_count,
                },
            )
        )

        return task
