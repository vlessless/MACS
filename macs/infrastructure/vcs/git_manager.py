"""Git implementation of the IVersionControlProvider interface."""

import git
from git import Repo
from uuid import UUID

from macs.domain.exceptions import RepositoryStateError, GitSyncConflictError
from macs.domain.interfaces import IVersionControlProvider


class GitVersionControlProvider(IVersionControlProvider):
    """Manages Git-based checkpointing for the Stash & Sync protocol."""

    def __init__(self, repo_path: str = ".") -> None:
        """Initializes the Git provider with the local repository path.

        Args:
            repo_path: The filesystem path to the git repository.
        """
        try:
            self._repo = Repo(repo_path)
        except git.exc.InvalidGitRepositoryError as e:
            raise RepositoryStateError(f"Not a valid git repository: {e}") from e

    async def create_checkpoint(self, task_id: UUID) -> str:
        """Saves current work and cuts a human-fix-checkpoint branch."""
        if self._repo.head.is_detached:
            raise RepositoryStateError(
                "Cannot create checkpoint in detached HEAD state."
            )

        branch_name = f"human-fix-checkpoint-{task_id.hex[:8]}"

        try:
            self._repo.git.stash("save", "MACS_INTERNAL_STASH")
        except git.exc.GitCommandError as e:
            if "No local changes to save" not in str(e):
                raise RepositoryStateError(f"Stash failed: {e}") from e

        try:
            self._repo.git.checkout("-b", branch_name)
        except git.exc.GitCommandError:
            self._repo.git.checkout(branch_name)

        return branch_name

    async def sync_checkpoint(self, task_id: UUID) -> None:
        """Resumes work from a checkpoint, popping stashes and merging."""
        try:
            self._repo.git.stash("pop")
        except git.exc.GitCommandError as e:
            if "conflict" in str(e).lower():
                raise GitSyncConflictError("Merge conflict during stash pop.") from e
            raise RepositoryStateError(f"Sync failed: {e}") from e

    async def get_diff(self, base_branch: str, head_branch: str) -> str:
        """Generates a diff between branches."""
        try:
            return str(self._repo.git.diff(f"{base_branch}..{head_branch}"))
        except git.exc.GitCommandError as e:
            raise RepositoryStateError(f"Diff generation failed: {e}") from e
