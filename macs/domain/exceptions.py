"""Custom Domain Exceptions for error handling and Thought Traces."""


class MACSDomainException(Exception):
    """Base exception for all domain-related errors."""

    pass


class MaxStrikesExceededError(MACSDomainException):
    """Raised when a task hits the 5th strike and requires human intervention."""

    pass


class ConsensusNotReachedError(MACSDomainException):
    """Raised when TL agents fail to reach a majority vote on a proposal."""

    pass
