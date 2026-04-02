"""Unit tests for the TaskOrchestrator."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from macs.application.orchestrator import TaskOrchestrator
from macs.domain.entities import MAX_STRIKE_COUNT, Task
from macs.domain.enums import TaskStatus
from macs.domain.interfaces import IIntegrationProvider, IQueueProvider, IUnitOfWork


class TestTaskOrchestrator:
    """Test suite for the TaskOrchestrator with Atomic Unit of Work."""

    @pytest.fixture
    def mock_uow(self) -> MagicMock:
        """Provides a mocked IUnitOfWork with async context manager support."""
        uow = MagicMock(spec=IUnitOfWork)
        uow.tasks = AsyncMock()
        uow.__aenter__.return_value = uow
        uow.__aexit__.return_value = None
        uow.commit = AsyncMock()
        uow.rollback = AsyncMock()
        return uow

    @pytest.fixture
    def mock_queue(self) -> MagicMock:
        """Provides a mocked IQueueProvider."""
        return MagicMock(spec=IQueueProvider)

    @pytest.fixture
    def mock_integration(self) -> MagicMock:
        """Provides a mocked IIntegrationProvider."""
        integration = MagicMock(spec=IIntegrationProvider)
        integration.broadcast = AsyncMock()
        return integration

    @pytest.fixture
    def orchestrator(
        self,
        mock_uow: MagicMock,
        mock_queue: MagicMock,
        mock_integration: MagicMock,
    ) -> TaskOrchestrator:
        """Initializes the orchestrator with mocked dependencies."""
        return TaskOrchestrator(
            uow=mock_uow,
            queue=mock_queue,
            integration=mock_integration,
        )

    @pytest.mark.asyncio
    async def test_process_task_pending_to_in_progress(
        self,
        orchestrator: TaskOrchestrator,
        mock_uow: MagicMock,
        mock_integration: MagicMock,
    ) -> None:
        """Tests the transition from PENDING to IN_PROGRESS using UoW."""
        task_id = uuid4()
        task = Task(
            id=task_id,
            title="Test Task",
            description="Testing",
            status=TaskStatus.PENDING,
        )
        mock_uow.tasks.get_task.return_value = task

        await orchestrator.process_task(task_id)

        assert task.status == TaskStatus.IN_PROGRESS
        mock_uow.tasks.update_task.assert_called_once_with(task)
        mock_uow.commit.assert_called_once()

        # Verify Thought Trace broadcast
        mock_integration.broadcast.assert_called_once()
        log_call = mock_integration.broadcast.call_args[0][0]
        assert log_call.action == "TRANSITION"
        assert log_call.agent == "Orchestrator"

    @pytest.mark.asyncio
    async def test_process_task_circuit_breaker_5_strikes(
        self,
        orchestrator: TaskOrchestrator,
        mock_uow: MagicMock,
        mock_integration: MagicMock,
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

        mock_uow.tasks.get_task.return_value = task

        async def failing_handler(t: Task) -> Task:
            t.increment_strike()
            return t

        orchestrator._dispatch_table[TaskStatus.IN_PROGRESS] = failing_handler

        await orchestrator.process_task(task_id)

        assert task.status == TaskStatus.STALLED_FOR_HUMAN
        assert task.post_mortem_report is not None
        mock_uow.tasks.update_task.assert_called_once()
        mock_uow.commit.assert_called_once()

        # Verify Critical Escalation broadcast
        calls = mock_integration.broadcast.call_args_list
        assert any(c[0][0].action == "INTERVENTION_REQUIRED" for c in calls)
        assert any(c[0][0].priority.value == "CRITICAL" for c in calls)
