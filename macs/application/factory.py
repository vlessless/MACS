"""Application Factory for Dependency Injection.

Reasoning:
    The factory acts as the 'Assembler' of the MACS system. It initializes
    concrete infrastructure implementations and injects them into the
    Orchestrator, satisfying the Dependency Inversion Principle.
"""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from macs.application.orchestrator import TaskOrchestrator
from macs.domain.interfaces import IQueueProvider
from macs.infrastructure.config import SystemSettings
from macs.infrastructure.container.docker_client import DockerContainerProvider
from macs.infrastructure.integration.websocket_provider import ws_provider
from macs.infrastructure.persistence.uow import PostgresUnitOfWork


class ApplicationFactory:
    """Assembles the MACS system components."""

    @staticmethod
    def create_orchestrator(
        settings: SystemSettings, queue: IQueueProvider
    ) -> TaskOrchestrator:
        """Wires up the Orchestrator with initialized infrastructure dependencies.

        Args:
            settings: Validated system configuration.
            queue: The initialized queue provider (e.g., Redis).

        Returns:
            TaskOrchestrator: The fully assembled system brain.
        """
        # Infrastructure Initialization
        engine = create_async_engine(settings.get_database_url())
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        uow = PostgresUnitOfWork(session_factory)

        # Docker provider is available for use within Task handlers via the Orchestrator
        # or can be injected if logic requires direct container interaction.
        _ = DockerContainerProvider(base_image=settings.get_docker_base_image())

        return TaskOrchestrator(uow=uow, queue=queue, integration=ws_provider)
