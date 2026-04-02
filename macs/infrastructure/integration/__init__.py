"""MACS Integration Layer: Real-time observability and external event bridges.

This package contains adapters that facilitate transparency into the agent
hierarchy, primarily through WebSocket-based 'Thought Trace' broadcasting
and interaction protocols for human supervisors.
"""

from .websocket_provider import WebSocketIntegrationProvider

__all__ = ["WebSocketIntegrationProvider"]
