"""Unit tests for the ConsensusService."""

from uuid import uuid4

import pytest

from macs.application.consensus import ConsensusService
from macs.domain.entities import ConsensusVote, Task


class TestConsensusService:
    """Test suite for Hybrid Consensus logic.

    Ensures that approval and rejection thresholds are strictly enforced
    and supports early-exit optimization.
    """

    @pytest.fixture
    def service(self) -> ConsensusService:
        """Returns an instance of the ConsensusService."""
        return ConsensusService()

    @pytest.fixture
    def mock_task(self) -> Task:
        """Returns a generic Task entity for evaluation."""
        return Task(title="Consensus Test", description="Testing vote logic")

    def test_evaluate_consensus_early_exit_approve(
        self, service: ConsensusService, mock_task: Task
    ) -> None:
        """Verifies early exit when 2 positive votes are reached."""
        votes = [
            ConsensusVote(agent_id=uuid4(), vote=True, raw_rationale="Good"),
            ConsensusVote(agent_id=uuid4(), vote=True, raw_rationale="Perfect"),
            ConsensusVote(
                agent_id=uuid4(), vote=False, raw_rationale="Wait"
            ),  # Should be ignored
        ]

        result = service.evaluate_consensus(mock_task, votes)

        assert result.is_approved is True
        assert result.is_final is True
        # Rationale should only contain the votes processed up to the exit
        assert "Good" in result.summary_rationale
        assert "Perfect" in result.summary_rationale

    def test_evaluate_consensus_early_exit_reject(
        self, service: ConsensusService, mock_task: Task
    ) -> None:
        """Verifies early exit when 2 negative votes are reached."""
        votes = [
            ConsensusVote(agent_id=uuid4(), vote=False, raw_rationale="Bad"),
            ConsensusVote(agent_id=uuid4(), vote=False, raw_rationale="Horrible"),
            ConsensusVote(agent_id=uuid4(), vote=True, raw_rationale="I liked it"),
        ]

        result = service.evaluate_consensus(mock_task, votes)

        assert result.is_approved is False
        assert result.is_final is True
        assert "Bad" in result.summary_rationale
        assert "Horrible" in result.summary_rationale

    def test_evaluate_consensus_full_house_mixed(
        self, service: ConsensusService, mock_task: Task
    ) -> None:
        """Tests a 2-approve, 1-reject scenario where order matters."""
        votes = [
            ConsensusVote(agent_id=uuid4(), vote=True, raw_rationale="Yes 1"),
            ConsensusVote(agent_id=uuid4(), vote=False, raw_rationale="No 1"),
            ConsensusVote(agent_id=uuid4(), vote=True, raw_rationale="Yes 2"),
        ]

        result = service.evaluate_consensus(mock_task, votes)

        assert result.is_approved is True
        assert result.is_final is True
        assert "Yes 1 | No 1 | Yes 2" == result.summary_rationale

    def test_evaluate_consensus_insufficient_votes(
        self, service: ConsensusService, mock_task: Task
    ) -> None:
        """Verifies that is_final is False if thresholds aren't met."""
        votes = [
            ConsensusVote(agent_id=uuid4(), vote=True, raw_rationale="Only one vote"),
        ]

        result = service.evaluate_consensus(mock_task, votes)

        assert result.is_final is False
        assert result.is_approved is False
        assert result.summary_rationale == "Only one vote"
