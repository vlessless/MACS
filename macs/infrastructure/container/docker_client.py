"""Docker implementation of the IContainerProvider interface."""

import os
import time
from typing import cast
from uuid import UUID

import docker
from docker.errors import APIError, DockerException, ImageNotFound
from docker.models.containers import Container

from macs.domain.entities import ExecutionResult
from macs.domain.exceptions import ExecutionFailedError
from macs.domain.interfaces import IContainerProvider


class DockerContainerProvider(IContainerProvider):
    """Manages execution of agent tasks within sibling Docker containers."""

    def __init__(
        self,
        base_image: str = "python:3.12-slim",
        workspace_path: str | None = None,
    ) -> None:
        """Initializes the provider with Docker client and workspace context.

        Args:
            base_image: The Docker image used for the execution environment.
            workspace_path: Host path to mount. Defaults to current directory.
        """
        try:
            self._client = docker.from_env()
        except DockerException as err:
            raise ExecutionFailedError(
                f"Failed to connect to Docker socket: {err}"
            ) from err

        self._base_image = base_image
        self._workspace_host = workspace_path or os.getcwd()
        self._container_workdir = "/app"

    async def run_task(self, task_id: UUID, command: list[str]) -> ExecutionResult:
        """Executes a command inside a sibling container."""
        container: Container | None = None
        start_time = time.perf_counter()

        try:
            container = cast(
                Container,
                self._client.containers.create(
                    image=self._base_image,
                    command=command,
                    name=f"macs-task-{task_id.hex[:8]}-{int(start_time)}",
                    mem_limit="512m",
                    cpu_period=100000,
                    cpu_quota=50000,
                    network_disabled=True,
                    volumes={
                        self._workspace_host: {
                            "bind": self._container_workdir,
                            "mode": "rw",
                        }
                    },
                    working_dir=self._container_workdir,
                    detach=True,
                ),
            )

            container.start()
            status_code_raw = container.wait()
            exit_code = int(status_code_raw.get("StatusCode", 1))

            stdout = container.logs(stdout=True, stderr=False).decode("utf-8")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8")

            duration = time.perf_counter() - start_time

            return ExecutionResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                duration=round(duration, 3),
            )

        except (APIError, ImageNotFound, DockerException) as err:
            raise ExecutionFailedError(
                f"Container execution failed: {str(err)}"
            ) from err

        finally:
            if container:
                try:
                    container.remove(force=True, v=True)
                except Exception:
                    pass
