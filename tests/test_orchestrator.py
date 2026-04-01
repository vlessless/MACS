"""Unit tests for the TaskOrchestrator."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from macs.application.orchestrator import TaskOrchestrator
from macs.domain.entities import MAX_STRIKE_COUNT, Task
from macs.domain.enums import TaskStatus
from macs.domain.interfaces import IQueueProvider, IStateRepository


class TestTaskOrchestrator:
    """Test suite for the TaskOrchestrator application layer.

    This suite verifies state transitions, error handling, and the
    5-Strike Rule enforcement logic.
    """

    @pytest.fixture
    def mock_repo(self) -> MagicMock:
        """Provides a mocked IStateRepository.

        Returns:
            MagicMock: A mock instance of the state repository.
        """
        return MagicMock(spec=IStateRepository)

    @pytest.fixture
    def mock_queue(self) -> MagicMock:
        """Provides a mocked IQueueProvider.

        Returns:
            MagicMock: A mock instance of the queue provider.
        """
        return MagicMock(spec=IQueueProvider)

    @pytest.fixture
    def orchestrator(
        self, mock_repo: MagicMock, mock_queue: MagicMock
    ) -> TaskOrchestrator:
        """Initializes the orchestrator with mocked dependencies.

        Args:
            mock_repo: The mocked repository fixture.
            mock_queue: The mocked queue fixture.

        Returns:
            TaskOrchestrator: An instance of the orchestrator for testing.
        """
        return TaskOrchestrator(repository=mock_repo, queue=mock_queue)

    @pytest.mark.asyncio
    async def test_process_task_pending_to_in_progress(
        self, orchestrator: TaskOrchestrator, mock_repo: MagicMock
    ) -> None:
        """Tests the transition from PENDING to IN_PROGRESS.

        Args:
            orchestrator: The orchestrator instance.
            mock_repo: The mocked repository.
        """
        # Arrange
        task_id = uuid4()
        task = Task(
            id=task_id,
            title="Test Task",
            description="Testing",
            status=TaskStatus.PENDING,
        )
        mock_repo.get_task.return_value = task

        # Act
        await orchestrator.process_task(task_id)

        # Assert
        assert task.status == TaskStatus.IN_PROGRESS
        mock_repo.update_task.assert_called_once_with(task)
        assert any(entry["to"] == "IN_PROGRESS" for entry in task.thought_trace)

    @pytest.mark.asyncio
    async def test_process_task_not_found(
        self, orchestrator: TaskOrchestrator, mock_repo: MagicMock
    ) -> None:
        """Ensures RuntimeError is raised if task is missing from repo.

        Args:
            orchestrator: The orchestrator instance.
            mock_repo: The mocked repository.
        """
        mock_repo.get_task.return_value = None

        with pytest.raises(RuntimeError, match="not found in repository"):
            await orchestrator.process_task(uuid4())

    @pytest.mark.asyncio
    async def test_process_task_invalid_status(
        self, orchestrator: TaskOrchestrator, mock_repo: MagicMock
    ) -> None:
        """Ensures ValueError is raised for statuses without handlers.

        Args:
            orchestrator: The orchestrator instance.
            mock_repo: The mocked repository.
        """
        task_id = uuid4()
        task = Task(
            id=task_id, title="Test", description="Test", status=TaskStatus.COMPLETED
        )
        mock_repo.get_task.return_value = task

        with pytest.raises(ValueError, match="No handler registered"):
            await orchestrator.process_task(task_id)

    @pytest.mark.asyncio
    async def test_process_task_circuit_breaker_5_strikes(
        self, orchestrator: TaskOrchestrator, mock_repo: MagicMock
    ) -> None:
        """Simulates the 5th strike and verifies Post-Mortem generation.

        Args:
            orchestrator: The orchestrator instance.
            mock_repo: The mocked repository.
        """
        # Arrange
        task_id = uuid4()
        task = Task(
            id=task_id,
            title="Failing Task",
            description="Will strike out",
            status=TaskStatus.IN_PROGRESS,
        )

        # Manually force task to its strike limit using domain constant
        for _ in range(MAX_STRIKE_COUNT):
            task.increment_strike()

        mock_repo.get_task.return_value = task

        async def failing_handler(t: Task) -> Task:
            """Simulates a handler failure that triggers the final strike."""
            t.increment_strike()
            return t

        orchestrator._dispatch_table[TaskStatus.IN_PROGRESS] = failing_handler

        # Act
        await orchestrator.process_task(task_id)

        # Assert
        assert task.status == TaskStatus.STALLED_FOR_HUMAN
        assert task.post_mortem_report is not None
        assert str(MAX_STRIKE_COUNT) in task.post_mortem_report.hypothesis
        assert task.strike_count == MAX_STRIKE_COUNT
        mock_repo.update_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_stalled_no_op(
        self, orchestrator: TaskOrchestrator, mock_repo: MagicMock
    ) -> None:
        """Verifies that processing a STALLED task results in no state changes.

        Args:
            orchestrator: The orchestrator instance.
            mock_repo: The mocked repository.
        """
        task_id = uuid4()
        task = Task(
            id=task_id,
            title="Stalled",
            description="...",
            status=TaskStatus.STALLED_FOR_HUMAN,
        )
        mock_repo.get_task.return_value = task

        # Act
        await orchestrator.process_task(task_id)

        # Assert
        assert task.status == TaskStatus.STALLED_FOR_HUMAN
        mock_repo.update_task.assert_called_once_with(task)

    @pytest.mark.asyncio
    async def test_handle_in_progress_no_op_logic(
        self, orchestrator: TaskOrchestrator, mock_repo: MagicMock
    ) -> None:
        """Verifies that processing an IN_PROGRESS task remains IN_PROGRESS.

        Args:
            orchestrator: The orchestrator instance.
            mock_repo: The mocked repository.
        """
        task_id = uuid4()
        task = Task(
            id=task_id,
            title="Progress",
            description="...",
            status=TaskStatus.IN_PROGRESS,
        )
        mock_repo.get_task.return_value = task

        # Act
        await orchestrator.process_task(task_id)

        # Assert
        assert task.status == TaskStatus.IN_PROGRESS
        mock_repo.update_task.assert_called_once_with(task)
