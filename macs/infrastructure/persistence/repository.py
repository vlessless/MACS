"""Postgres implementation of the IStateRepository."""

from collections.abc import AsyncGenerator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from macs.domain.entities import Agent, ConsensusVote, Task
from macs.domain.enums import TaskStatus
from macs.domain.interfaces import IStateRepository
from macs.infrastructure.persistence.mappers import DomainMapper
from macs.infrastructure.persistence.models import ConsensusVoteTable, TaskTable


class PostgresStateRepository(IStateRepository):
    """SQLAlchemy-based implementation of system state persistence.

    Uses AsyncSession for non-blocking database operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initializes the repository with an active async session.

        Args:
            session: An active SQLAlchemy AsyncSession.
        """
        self._session = session

    async def get_task(self, task_id: UUID) -> Task | None:
        """Retrieves and maps a task from the database.

        Args:
            task_id: The UUID of the task.

        Returns:
            Task | None: The domain entity or None if not found.
        """
        stmt = select(TaskTable).where(TaskTable.id == task_id)
        result = (await self._session.execute(stmt)).scalar_one_or_none()
        return DomainMapper.to_domain_task(result) if result else None

    async def update_task(self, task: Task) -> None:
        """Updates or creates a task in the database.

        Args:
            task: The Domain Task entity to persist.
        """
        table_data = DomainMapper.to_table_task(task)
        db_task = await self._session.get(TaskTable, task.id)

        if db_task:
            for key, value in table_data.items():
                setattr(db_task, key, value)
        else:
            new_task = TaskTable(**table_data)
            self._session.add(new_task)

    async def save_agent(self, agent: Agent) -> None:
        """Saves agent status (Implementation pending Infrastructure Role)."""
        pass

    async def add_vote(self, task_id: UUID, vote: ConsensusVote) -> None:
        """Persists a TL vote to the database.

        Args:
            task_id: ID of the task being voted on.
            vote: The ConsensusVote domain entity.
        """
        db_vote = ConsensusVoteTable(
            task_id=task_id,
            agent_id=vote.agent_id,
            vote=vote.vote,
            raw_rationale=vote.raw_rationale,
            timestamp=vote.timestamp,
        )
        self._session.add(db_vote)

    async def get_votes(self, task_id: UUID) -> list[ConsensusVote]:
        """Retrieves and maps all votes for a given task.

        Args:
            task_id: The UUID of the task.

        Returns:
            list[ConsensusVote]: A list of mapped domain vote entities.
        """
        stmt = select(ConsensusVoteTable).where(ConsensusVoteTable.task_id == task_id)
        result = await self._session.execute(stmt)

        vote_entities: list[ConsensusVote] = []
        for row in result.scalars():
            vote_entities.append(DomainMapper.to_domain_vote(row))

        return vote_entities

    async def stream_active_tasks(self) -> AsyncGenerator[Task, None]:
        """Streams active tasks using an async generator for memory efficiency.

        Yields:
            Task: The next active domain task entity.
        """
        terminal_states = [TaskStatus.COMPLETED, TaskStatus.STALLED_FOR_HUMAN]
        stmt = select(TaskTable).where(TaskTable.status.notin_(terminal_states))

        result = await self._session.stream_scalars(stmt)
        async for task_row in result:
            yield DomainMapper.to_domain_task(task_row)
