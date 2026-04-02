"""Unit tests for the TaskOrchestrator."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from macs.application.orchestrator import TaskOrchestrator
from macs.domain.entities import MAX_STRIKE_COUNT, ConsensusResult, Task
from macs.domain.enums import TaskStatus
from macs.domain.interfaces import (
    IConsensusService,
    IContainerProvider,
    IIntegrationProvider,
    InfrastructureManifest,
    IQueueProvider,
    IUnitOfWork,
    IVersionControlProvider,
)


class TestTaskOrchestrator:
    """Test suite for the TaskOrchestrator using an Infrastructure Manifest.

    Reasoning:
        Testing in Mypy strict mode requires explicit casting of mocked
        interface methods to AsyncMock or MagicMock to access verification and
        configuration attributes like return_value.
    """

    @pytest.fixture
    def mock_manifest(self) -> InfrastructureManifest:
        """Provides a manifest filled with mocked infrastructure providers."""
        uow = MagicMock(spec=IUnitOfWork)
        uow.tasks = MagicMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=None)
        uow.commit = AsyncMock()
        uow.rollback = AsyncMock()

        # Specifically mock the async methods of the repository
        uow.tasks.get_task = AsyncMock()
        uow.tasks.update_task = AsyncMock()
        uow.tasks.get_votes = AsyncMock()

        integration = MagicMock(spec=IIntegrationProvider)
        integration.broadcast = AsyncMock()

        return InfrastructureManifest(
            uow=uow,
            queue=MagicMock(spec=IQueueProvider),
            integration=integration,
            container=MagicMock(spec=IContainerProvider),
            vcs=MagicMock(spec=IVersionControlProvider),
            consensus=MagicMock(spec=IConsensusService),
        )

    @pytest.fixture
    def orchestrator(self, mock_manifest: InfrastructureManifest) -> TaskOrchestrator:
        """Initializes the orchestrator with the mock manifest."""
        return TaskOrchestrator(manifest=mock_manifest)

    @pytest.mark.asyncio
    async def test_process_task_pending_to_in_progress(
        self,
        orchestrator: TaskOrchestrator,
        mock_manifest: InfrastructureManifest,
    ) -> None:
        """Tests the transition from PENDING to IN_PROGRESS."""
        task_id = uuid4()
        task = Task(
            id=task_id,
            title="Test Task",
            description="Testing",
            status=TaskStatus.PENDING,
        )

        # Cast to AsyncMock to satisfy Mypy strict mode
        get_task_mock = cast(AsyncMock, mock_manifest.uow.tasks.get_task)
        get_task_mock.return_value = task

        await orchestrator.process_task(task_id)

        assert task.status == TaskStatus.IN_PROGRESS

        update_task_mock = cast(AsyncMock, mock_manifest.uow.tasks.update_task)
        update_task_mock.assert_called_once_with(task)

        commit_mock = cast(AsyncMock, mock_manifest.uow.commit)
        commit_mock.assert_called_once()

        # Verify Thought Trace broadcast
        broadcast_mock = cast(AsyncMock, mock_manifest.integration.broadcast)
        broadcast_mock.assert_called_once()
        log_call = broadcast_mock.call_args[0][0]
        assert log_call.action == "TRANSITION"

    @pytest.mark.asyncio
    async def test_process_task_circuit_breaker_5_strikes(
        self,
        orchestrator: TaskOrchestrator,
        mock_manifest: InfrastructureManifest,
    ) -> None:
        """Verifies the 5-strike rule and commit on HALT."""
        task_id = uuid4()
        task = Task(
            id=task_id,
            title="Failing Task",
            description="Will strike out",
            status=TaskStatus.IN_PROGRESS,
        )

        for _ in range(MAX_STRIKE_COUNT):
            task.increment_strike()

        get_task_mock = cast(AsyncMock, mock_manifest.uow.tasks.get_task)
        get_task_mock.return_value = task

        async def failing_handler(t: Task) -> Task:
            """Simulates logic that triggers the final strike."""
            t.increment_strike()
            return t

        # Bypass the standard handler for test injection
        # Use type: ignore for internal dispatch table modification during test
        orchestrator._dispatch_table[TaskStatus.IN_PROGRESS] = failing_handler

        await orchestrator.process_task(task_id)

        assert task.status == TaskStatus.STALLED_FOR_HUMAN
        assert task.post_mortem_report is not None

        commit_mock = cast(AsyncMock, mock_manifest.uow.commit)
        commit_mock.assert_called_once()

        # Verify Critical Escalation broadcast
        broadcast_mock = cast(AsyncMock, mock_manifest.integration.broadcast)
        calls = broadcast_mock.call_args_list
        assert any(c[0][0].action == "INTERVENTION_REQUIRED" for c in calls)

    @pytest.mark.asyncio
    async def test_process_task_tl_review_approved(
        self,
        orchestrator: TaskOrchestrator,
        mock_manifest: InfrastructureManifest,
    ) -> None:
        """Tests successful transition from TL_REVIEW to COMPLETED."""
        task_id = uuid4()
        task = Task(
            id=task_id,
            title="Review Task",
            description="Awaiting approval",
            status=TaskStatus.TL_REVIEW,
        )

        cast(AsyncMock, mock_manifest.uow.tasks.get_task).return_value = task
        cast(AsyncMock, mock_manifest.uow.tasks.get_votes).return_value = []

        # Cast to MagicMock to satisfy Mypy strict mode for sync method return_value
        evaluate_mock = cast(MagicMock, mock_manifest.consensus.evaluate_consensus)
        evaluate_mock.return_value = ConsensusResult(
            is_approved=True,
            is_final=True,
            summary_rationale="LGTM",
        )

        await orchestrator.process_task(task_id)

        assert task.status == TaskStatus.COMPLETED
        assert task.strike_count == 0

    @pytest.mark.asyncio
    async def test_process_task_tl_review_rejected(
        self,
        orchestrator: TaskOrchestrator,
        mock_manifest: InfrastructureManifest,
    ) -> None:
        """Tests transition from TL_REVIEW back to IN_PROGRESS on rejection."""
        task_id = uuid4()
        initial_strikes = 1
        expected_strikes = 2
        task = Task(
            id=task_id,
            title="Review Task",
            description="Will be rejected",
            status=TaskStatus.TL_REVIEW,
            strike_count=initial_strikes,
        )

        cast(AsyncMock, mock_manifest.uow.tasks.get_task).return_value = task
        cast(AsyncMock, mock_manifest.uow.tasks.get_votes).return_value = []

        # Cast to MagicMock to satisfy Mypy strict mode for sync method return_value
        evaluate_mock = cast(MagicMock, mock_manifest.consensus.evaluate_consensus)
        evaluate_mock.return_value = ConsensusResult(
            is_approved=False,
            is_final=True,
            summary_rationale="Major bugs found",
        )

        await orchestrator.process_task(task_id)

        assert task.status == TaskStatus.IN_PROGRESS
        assert task.strike_count == expected_strikes
