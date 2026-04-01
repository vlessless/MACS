"""SQLAlchemy implementation of the Atomic Unit of Work."""

from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from macs.domain.exceptions import PersistenceError
from macs.domain.interfaces import IUnitOfWork
from macs.infrastructure.persistence.repository import PostgresStateRepository


class PostgresUnitOfWork(IUnitOfWork):
    """Manages transactional integrity for Postgres storage operations."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Initializes the Unit of Work with a session factory.

        Args:
            session_factory: The factory for creating AsyncSessions.
        """
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        """Initializes the async session and links the repository.

        Returns:
            Self: The active Unit of Work instance.
        """
        self._session = self._session_factory()
        self.tasks = PostgresStateRepository(self._session)
        return self

    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        """Safely closes the session, performing a rollback if an error occurred.

        Args:
            exc_type: The exception type if one occurred.
            exc_val: The exception instance.
            exc_tb: The traceback.
        """
        if self._session:
            if exc_type:
                await self.rollback()
            await self._session.close()

    async def commit(self) -> None:
        """Commits all pending changes to the database.

        Raises:
            PersistenceError: If no active session exists to commit.
        """
        if not self._session:
            raise PersistenceError("No active transaction found to commit.")
        await self._session.commit()

    async def rollback(self) -> None:
        """Rolls back all pending changes in the current transaction.

        Raises:
            PersistenceError: If no active session exists to rollback.
        """
        if not self._session:
            raise PersistenceError("No active transaction found to rollback.")
        await self._session.rollback()
