"""MACS Domain Layer: Entities, Enums, and Interfaces."""

from .entities import Agent, ConsensusVote, ExecutionResult, PostMortemReport, Task
from .enums import AgentRole, TaskStatus
from .exceptions import (
    ConsensusNotReachedError,
    MACSDomainException,
    MaxStrikesExceededError,
    PersistenceError,
)
from .interfaces import IQueueProvider, IStateRepository, IUnitOfWork

__all__ = [
    "Agent",
    "ConsensusVote",
    "ExecutionResult",
    "PostMortemReport",
    "Task",
    "AgentRole",
    "TaskStatus",
    "MACSDomainException",
    "MaxStrikesExceededError",
    "ConsensusNotReachedError",
    "PersistenceError",
    "IStateRepository",
    "IQueueProvider",
    "IUnitOfWork",
]
