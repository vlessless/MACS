"""Custom Domain Exceptions for error handling and Thought Traces."""


class MACSDomainException(Exception):
    """Base exception for all domain-related errors."""

    pass


class MaxStrikesExceededError(MACSDomainException):
    """Raised when a task hits the 5th strike and requires human intervention."""

    def __init__(self, message: str) -> None:
        """Initializes the exception with a descriptive message.

        Args:
            message: The rationale for the halt.
        """
        super().__init__(message)


class ConsensusNotReachedError(MACSDomainException):
    """Raised when TL agents fail to reach a majority vote on a proposal."""

    pass


class PersistenceError(MACSDomainException):
    """Raised when a persistent operation (commit/rollback) fails."""

    pass


class ExecutionFailedError(MACSDomainException):
    """Raised when a Sibling Container fails to start or crashes internally."""

    pass


class RepositoryStateError(MACSDomainException):
    """Raised when the git repository is in an invalid state for an operation."""

    pass


class GitSyncConflictError(MACSDomainException):
    """Raised when a stash pop or merge fails during the resumption phase."""

    pass
