"""Unit tests for the DockerContainerProvider."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from macs.infrastructure.container.docker_client import DockerContainerProvider


class TestDockerContainerProvider:
    """Test suite for Docker sibling container execution."""

    @pytest.fixture
    def mock_docker_client(self) -> Generator[MagicMock, None, None]:
        """Provides a mocked docker-py client."""
        with patch("docker.from_env") as mock_env:
            client = MagicMock()
            mock_env.return_value = client
            yield client

    @pytest.fixture
    def provider(self, mock_docker_client: MagicMock) -> DockerContainerProvider:
        """Initializes the provider with mocked client."""
        return DockerContainerProvider()

    @pytest.mark.asyncio
    async def test_run_task_success(
        self, provider: DockerContainerProvider, mock_docker_client: MagicMock
    ) -> None:
        """Verifies successful container execution and resource mapping."""
        mock_container = MagicMock()
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.side_effect = [b"output", b""]

        task_id = uuid4()
        result = await provider.run_task(task_id, ["pytest"])

        assert result.exit_code == 0
        mock_container.remove.assert_called_once()
