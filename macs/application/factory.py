"""Application Factory for Dependency Injection.

Reasoning:
    The factory acts as the 'Assembler' of the MACS system. It initializes
    concrete infrastructure implementations and injects them into the
    Orchestrator, satisfying the Dependency Inversion Principle.
"""

from macs.application.orchestrator import TaskOrchestrator
from macs.domain.interfaces import (
    InfrastructureManifest,
    IQueueProvider,
    IUnitOfWork,
)
from macs.infrastructure.config import SystemSettings
from macs.infrastructure.container.docker_client import DockerContainerProvider
from macs.infrastructure.integration.websocket_provider import ws_provider
from macs.infrastructure.vcs.git_manager import GitVersionControlProvider


class ApplicationFactory:
    """Assembles the MACS system components."""

    @staticmethod
    def create_orchestrator(
        settings: SystemSettings, uow: IUnitOfWork, queue: IQueueProvider
    ) -> TaskOrchestrator:
        """Wires up the Orchestrator with initialized infrastructure dependencies.

        Args:
            settings: Validated system configuration.
            uow: Initialized Persistence Unit of Work.
            queue: Initialized Queue Provider.

        Returns:
            TaskOrchestrator: The fully assembled system brain with all limbs.
        """
        # Initialize providers
        container_provider = DockerContainerProvider(
            base_image=settings.get_docker_base_image()
        )
        vcs_provider = GitVersionControlProvider(repo_path=".")

        # Pack into manifest to avoid constructor argument bloat
        manifest = InfrastructureManifest(
            uow=uow,
            queue=queue,
            integration=ws_provider,
            container=container_provider,
            vcs=vcs_provider,
        )

        return TaskOrchestrator(manifest=manifest)
