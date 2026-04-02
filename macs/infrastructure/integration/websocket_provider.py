"""FastAPI WebSocket implementation of the Integration Provider."""

import asyncio
from contextlib import asynccontextmanager
from typing import Any
from collections.abc import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from macs.domain.entities import ThoughtLog
from macs.domain.enums import EventPriority
from macs.domain.interfaces import IIntegrationProvider


class ConnectionManager:
    """Manages active WebSocket connections and broadcasting."""

    def __init__(self) -> None:
        """Initializes the manager with an empty set of active sockets."""
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts a new socket and registers it."""
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Removes a socket from the active set."""
        self.active_connections.remove(websocket)

    async def broadcast_json(self, message: dict[str, Any]) -> None:
        """Sends a JSON message to all clients, ignoring dead sockets."""
        disconnected_sockets: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected_sockets.append(connection)

        for socket in disconnected_sockets:
            self.active_connections.remove(socket)


class WebSocketIntegrationProvider(IIntegrationProvider):
    """Integration adapter providing a real-time Thought Trace via WebSockets."""

    def __init__(
        self, manager_instance: ConnectionManager, max_queue_size: int = 100
    ) -> None:
        """Initializes the provider with a manager and buffer."""
        self._manager = manager_instance
        self._queue: asyncio.Queue[ThoughtLog] = asyncio.Queue(maxsize=max_queue_size)
        self._worker_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Starts the background broadcast worker."""
        self._worker_task = asyncio.create_task(self._broadcast_worker())

    async def stop(self) -> None:
        """Gracefully shuts down the worker task."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def _broadcast_worker(self) -> None:
        """Continuously pulls from the queue and broadcasts to clients."""
        while True:
            log_entity = await self._queue.get()
            # Prepare message for wire transfer (Serialize datetime to string)
            message = log_entity.model_dump()
            message["timestamp"] = log_entity.timestamp.isoformat()
            message["priority"] = log_entity.priority.value

            await self._manager.broadcast_json(message)
            self._queue.task_done()

    async def broadcast(self, log: ThoughtLog) -> None:
        """Enqueues a message for broadcasting.

        Implements basic backpressure: if the queue is full, LOW priority
        logs are discarded to keep the stream current for CRITICAL events.
        """
        if self._queue.full():
            if log.priority == EventPriority.LOW:
                return

        await self._queue.put(log)


# Global instances for the API
manager = ConnectionManager()
ws_provider = WebSocketIntegrationProvider(manager)


@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncGenerator[None, None]:
    """Manages the startup and shutdown of the WebSocket worker."""
    await ws_provider.start()
    yield
    await ws_provider.stop()


# FastAPI App Definition
app = FastAPI(title="MACS Integration Bridge", lifespan=lifespan)


@app.websocket("/ws/trace")  # type: ignore[misc]
async def websocket_endpoint(websocket: WebSocket) -> None:
    """The real-time event stream endpoint."""
    await manager.connect(websocket)
    try:
        while True:
            # Maintain connection with a heartbeat
            await asyncio.sleep(30)
            await websocket.send_json({"type": "HEARTBEAT"})
    except (WebSocketDisconnect, Exception):
        manager.disconnect(websocket)
