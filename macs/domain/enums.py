"""Enums for the MACS Domain Layer."""

from enum import Enum


class AgentRole(Enum):
    """Defines the specialized roles within the MACS hierarchy."""

    TL_BACKEND = "TL_BACKEND"
    TL_DEVOPS = "TL_DEVOPS"
    DEV_BACKEND = "DEV_BACKEND"
    DEV_FRONTEND = "DEV_FRONTEND"
    QA_GATEKEEPER = "QA_GATEKEEPER"
    INTEGRATION_OBSERVER = "INTEGRATION_OBSERVER"


class TaskStatus(Enum):
    """Represents the finite states of a Task within the Orchestrator state machine."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    GENERATING_CODE = "GENERATING_CODE"
    TL_REVIEW = "TL_REVIEW"
    STALLED_FOR_HUMAN = "STALLED_FOR_HUMAN"
    COMPLETED = "COMPLETED"
    FAILED_STRIKE_1 = "FAILED_STRIKE_1"
    FAILED_STRIKE_2 = "FAILED_STRIKE_2"
    FAILED_STRIKE_3 = "FAILED_STRIKE_3"
    FAILED_STRIKE_4 = "FAILED_STRIKE_4"
    FAILED_STRIKE_5 = "FAILED_STRIKE_5"
