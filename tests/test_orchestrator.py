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
    """Test suite for the TaskOrchestrator using an Infrastructure Manifest."""

    @pytest.fixture
    def mock_manifest(self) -> InfrastructureManifest:
        """Provides a manifest filled with mocked infrastructure providers."""
        uow = MagicMock(spec=IUnitOfWork)
        uow.tasks = MagicMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=None)
        uow.commit = AsyncMock()
        uow.rollback = AsyncMock()

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
        self, orchestrator: TaskOrchestrator, mock_manifest: InfrastructureManifest
    ) -> None:
        """Tests the transition from PENDING to IN_PROGRESS."""
        task_id = uuid4()
        task = Task(
            id=task_id,
            title="Test Task",
            description="Testing",
            status=TaskStatus.PENDING,
        )

        # Fixed E501: Broken into two lines
        get_task_mock = cast(AsyncMock, mock_manifest.uow.tasks.get_task)
        get_task_mock.return_value = task

        await orchestrator.process_task(task_id)

        assert task.status == TaskStatus.IN_PROGRESS
        cast(AsyncMock, mock_manifest.uow.tasks.update_task).assert_called_once()

    @pytest.mark.asyncio
    async def test_strike_limit_verification_5th_strike_halt(
        self, orchestrator: TaskOrchestrator, mock_manifest: InfrastructureManifest
    ) -> None:
        """Strike Limit Verification: Verify transition to STALLED_FOR_HUMAN.

        Scenario: Task is at 4 strikes, and a TL_REVIEW results in REJECTION.
        """
        task_id = uuid4()
        task = Task(
            id=task_id,
            title="Max Strike Test",
            description="Rejection on strike 5",
            status=TaskStatus.TL_REVIEW,
            strike_count=4,
        )

        cast(AsyncMock, mock_manifest.uow.tasks.get_task).return_value = task
        cast(AsyncMock, mock_manifest.uow.tasks.get_votes).return_value = []

        # Mock a rejection verdict
        cast(
            MagicMock, mock_manifest.consensus.evaluate_consensus
        ).return_value = ConsensusResult(
            is_approved=False,
            is_final=True,
            summary_rationale="Critical structural flaws.",
        )

        await orchestrator.process_task(task_id)

        # Assertions for Strike 5 Halt
        assert task.status == TaskStatus.STALLED_FOR_HUMAN
        # Fixed PLR2004: Used Constant instead of Magic Value 5
        assert task.strike_count == MAX_STRIKE_COUNT
        assert task.post_mortem_report is not None

        # Verify critical escalation broadcast
        broadcast_mock = cast(AsyncMock, mock_manifest.integration.broadcast)
        last_log = broadcast_mock.call_args[0][0]
        assert last_log.action == "INTERVENTION_REQUIRED"
        assert last_log.priority.value == "CRITICAL"

    @pytest.mark.asyncio
    async def test_empty_votes_stays_in_tl_review(
        self, orchestrator: TaskOrchestrator, mock_manifest: InfrastructureManifest
    ) -> None:
        """Empty State: Behavior when get_votes returns empty list."""
        task_id = uuid4()
        task = Task(
            id=task_id,
            title="Waiting Task",
            description="No votes yet",
            status=TaskStatus.TL_REVIEW,
        )

        cast(AsyncMock, mock_manifest.uow.tasks.get_task).return_value = task
        cast(AsyncMock, mock_manifest.uow.tasks.get_votes).return_value = []

        cast(
            MagicMock, mock_manifest.consensus.evaluate_consensus
        ).return_value = ConsensusResult(
            is_approved=False, is_final=False, summary_rationale=""
        )

        await orchestrator.process_task(task_id)

        assert task.status == TaskStatus.TL_REVIEW
        broadcast_mock = cast(AsyncMock, mock_manifest.integration.broadcast)
        last_log = broadcast_mock.call_args[0][0]
        assert last_log.action == "CONSENSUS_PENDING"
