"""Unit tests for the ConsensusService validation suite.

Mandatory Scenarios:
- Early Exit (2/2 approved)
- Early Exit (2/2 rejected)
- Full House (2/3 approved, 1/3 rejected)
- Insufficient (1 vote total)
- Race Condition Simulation (Simultaneous async arrivals)
"""

import asyncio
from uuid import uuid4

import pytest

from macs.application.consensus import ConsensusService
from macs.domain.entities import ConsensusVote, Task


class TestConsensusServiceValidation:
    """Validation suite for Hybrid Consensus logic."""

    @pytest.fixture
    def service(self) -> ConsensusService:
        """Returns an instance of the ConsensusService."""
        return ConsensusService()

    @pytest.fixture
    def mock_task(self) -> Task:
        """Returns a generic Task entity for evaluation."""
        return Task(title="Consensus Test", description="Testing vote logic")

    def test_early_exit_approve_2_0(
        self, service: ConsensusService, mock_task: Task
    ) -> None:
        """Boundary Test: Exactly 2 Approve vs 0 Reject triggers early exit."""
        votes = [
            ConsensusVote(agent_id=uuid4(), vote=True, raw_rationale="Approve 1"),
            ConsensusVote(agent_id=uuid4(), vote=True, raw_rationale="Approve 2"),
        ]

        result = service.evaluate_consensus(mock_task, votes)

        assert result.is_approved is True
        assert result.is_final is True
        assert "Approve 1 | Approve 2" == result.summary_rationale

    def test_early_exit_reject_0_2(
        self, service: ConsensusService, mock_task: Task
    ) -> None:
        """Boundary Test: Exactly 2 Reject vs 0 Approve triggers early exit."""
        votes = [
            ConsensusVote(agent_id=uuid4(), vote=False, raw_rationale="Reject 1"),
            ConsensusVote(agent_id=uuid4(), vote=False, raw_rationale="Reject 2"),
        ]

        result = service.evaluate_consensus(mock_task, votes)

        assert result.is_approved is False
        assert result.is_final is True
        assert "Reject 1 | Reject 2" == result.summary_rationale

    def test_full_house_mixed_2_1(
        self, service: ConsensusService, mock_task: Task
    ) -> None:
        """Scenario: 2 Approve vs 1 Reject (The 'Full House' majority)."""
        votes = [
            ConsensusVote(agent_id=uuid4(), vote=True, raw_rationale="Good"),
            ConsensusVote(agent_id=uuid4(), vote=False, raw_rationale="Bad"),
            ConsensusVote(agent_id=uuid4(), vote=True, raw_rationale="Better"),
        ]

        result = service.evaluate_consensus(mock_task, votes)

        assert result.is_approved is True
        assert result.is_final is True
        assert "Good | Bad | Better" == result.summary_rationale

    def test_insufficient_votes_single(
        self, service: ConsensusService, mock_task: Task
    ) -> None:
        """Scenario: Insufficient votes (1 total) stays in non-final state."""
        votes = [
            ConsensusVote(agent_id=uuid4(), vote=True, raw_rationale="Single vote"),
        ]

        result = service.evaluate_consensus(mock_task, votes)

        assert result.is_final is False
        assert result.is_approved is False
        assert result.summary_rationale == "Single vote"

    @pytest.mark.asyncio
    async def test_race_condition_simulation(
        self, service: ConsensusService, mock_task: Task
    ) -> None:
        """Validates behavior when multiple votes arrive 'simultaneously'.

        Reasoning:
            In an async environment, multiple agents might submit votes at once.
            The service must handle the batch provided by the repository
            deterministically regardless of the order within that batch.
        """

        async def get_vote(val: bool, reason: str) -> ConsensusVote:
            return ConsensusVote(agent_id=uuid4(), vote=val, raw_rationale=reason)

        # Simulate concurrent generation of votes
        vote_tasks = [
            get_vote(True, "Async 1"),
            get_vote(False, "Async 2"),
            get_vote(True, "Async 3"),
        ]
        votes = await asyncio.gather(*vote_tasks)

        result = service.evaluate_consensus(mock_task, list(votes))

        assert result.is_final is True
        assert result.is_approved is True
        assert "Async 1 | Async 2 | Async 3" == result.summary_rationale

    def test_empty_votes_state(
        self, service: ConsensusService, mock_task: Task
    ) -> None:
        """Verifies behavior when get_votes returns an empty list."""
        result = service.evaluate_consensus(mock_task, [])

        assert result.is_final is False
        assert result.is_approved is False
        assert result.summary_rationale == ""
