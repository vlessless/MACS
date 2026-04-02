"""MACS Domain Layer: Entities, Enums, and Interfaces."""

from .entities import (
    Agent,
    ConsensusResult,
    ConsensusVote,
    ExecutionResult,
    PostMortemReport,
    Task,
    ThoughtLog,
)
from .enums import AgentRole, EventPriority, TaskStatus
from .exceptions import (
    ConsensusNotReachedError,
    MACSDomainException,
    MaxStrikesExceededError,
    PersistenceError,
)
from .interfaces import (
    IConsensusService,
    IContainerProvider,
    IIntegrationProvider,
    IQueueProvider,
    IStateRepository,
    IUnitOfWork,
    IVersionControlProvider,
)

__all__ = [
    "Agent",
    "ConsensusResult",
    "ConsensusVote",
    "ExecutionResult",
    "PostMortemReport",
    "Task",
    "ThoughtLog",
    "AgentRole",
    "EventPriority",
    "TaskStatus",
    "MACSDomainException",
    "MaxStrikesExceededError",
    "ConsensusNotReachedError",
    "PersistenceError",
    "IStateRepository",
    "IQueueProvider",
    "IUnitOfWork",
    "IContainerProvider",
    "IIntegrationProvider",
    "IVersionControlProvider",
    "IConsensusService",
]
