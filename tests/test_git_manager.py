"""Unit tests for the GitVersionControlProvider."""

from unittest.mock import MagicMock, patch
from uuid import uuid4
from macs.infrastructure.vcs.git_manager import GitVersionControlProvider


class TestGitVersionControlProvider:
    """Test suite for Git-based version control provider."""

    @patch("git.Repo")
    def test_create_checkpoint_success(self, mock_repo: MagicMock) -> None:
        """Verifies that create_checkpoint initiates a stash and branch creation."""
        instance = mock_repo.return_value
        instance.head.is_detached = False

        provider = GitVersionControlProvider()
        import asyncio

        loop = asyncio.get_event_loop()

        branch = loop.run_until_complete(provider.create_checkpoint(uuid4()))
        assert "human-fix-checkpoint" in branch
        instance.git.checkout.assert_called()
