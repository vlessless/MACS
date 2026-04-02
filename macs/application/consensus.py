"""Consensus Service implementation for the MACS platform.

Reasoning:
    This service implements the 'Hybrid Consensus' business logic. It resides
    in the Application layer to keep the Domain entities pure while ensuring
    the decision-making logic is decoupled from the state machine (Orchestrator).
"""

from macs.domain.entities import ConsensusResult, ConsensusVote, Task
from macs.domain.interfaces import IConsensusService


class ConsensusService(IConsensusService):
    """Evaluates Team Lead votes to reach a verdict on code proposals.

    Attributes:
        APPROVE_THRESHOLD (int): The number of positive votes required for approval.
        REJECT_THRESHOLD (int): The number of negative votes required for rejection.
    """

    APPROVE_THRESHOLD: int = 2
    REJECT_THRESHOLD: int = 2

    def evaluate_consensus(
        self, task: Task, votes: list[ConsensusVote]
    ) -> ConsensusResult:
        """Analyzes team lead votes to determine if a task is approved or rejected.

        Args:
            task: The Task entity being reviewed.
            votes: A list of votes cast by team leads.

        Returns:
            ConsensusResult: The decision and summary of the review process.

        Reasoning:
            Following the Agent Handbook, this uses a standard for-loop instead
            of list comprehensions or sum() for maximum readability and
            complexity control. It supports early-exit once a threshold is met.
        """
        approve_count: int = 0
        reject_count: int = 0
        rationale_list: list[str] = []

        for vote in votes:
            # Increment counters based on the boolean vote
            if vote.vote is True:
                approve_count += 1
            else:
                reject_count += 1

            # Aggregate rationales for the Thought Trace
            rationale_list.append(vote.raw_rationale)

            # Early-Exit: Check if Approval threshold met
            if approve_count >= self.APPROVE_THRESHOLD:
                return ConsensusResult(
                    is_approved=True,
                    is_final=True,
                    summary_rationale=" | ".join(rationale_list),
                )

            # Early-Exit: Check if Rejection threshold met
            if reject_count >= self.REJECT_THRESHOLD:
                return ConsensusResult(
                    is_approved=False,
                    is_final=True,
                    summary_rationale=" | ".join(rationale_list),
                )

        # No threshold met: Consensus is not yet final
        return ConsensusResult(
            is_approved=False,
            is_final=False,
            summary_rationale=" | ".join(rationale_list),
        )
