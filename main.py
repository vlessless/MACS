"""Entry point for the MACS platform."""

import sys
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from macs.application.factory import ApplicationFactory
from macs.domain.interfaces import IQueueProvider
from macs.infrastructure.config import SystemSettings
from macs.infrastructure.persistence.uow import PostgresUnitOfWork


class StubQueueProvider(IQueueProvider):
    """Temporary Queue implementation to satisfy Milestone 1 requirements."""

    def push_task(self, task_id: UUID) -> None:
        """No-op push."""
        pass

    def pop_task(self) -> UUID | None:
        """No-op pop."""
        return None

    def get_queue_length(self) -> int:
        """Returns 0."""
        return 0


def main() -> None:
    """Initializes the MACS Application via the Factory Pattern."""
    try:
        # Load and validate environment configuration
        settings = SystemSettings()
    except ValidationError as e:
        print(f"Configuration Error: Missing required environment variables.\n{e}")
        sys.exit(1)

    # Persistence Layer Setup (Boundary of Infrastructure)
    engine = create_async_engine(settings.get_database_url())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    uow = PostgresUnitOfWork(session_factory)

    # Use the stub provider to satisfy strict typing
    queue = StubQueueProvider()

    # Assemble the system
    orchestrator = ApplicationFactory.create_orchestrator(
        settings=settings, uow=uow, queue=queue
    )

    print(f"MACS Orchestrator initialized successfully: {orchestrator}")


if __name__ == "__main__":
    main()
