"""Unit tests for the GitVersionControlProvider."""

import os
from uuid import uuid4

import git
import pytest

from macs.infrastructure.vcs.git_manager import GitVersionControlProvider


class TestGitVersionControlProvider:
    """Test suite for Git-based version control provider.

    Ensures that tests are isolated from the main source repository
    using the pytest tmp_path fixture.
    """

    @pytest.fixture
    def isolated_repo(self, tmp_path: str) -> str:
        """Creates a temporary git repository for isolated testing."""
        repo_dir = tmp_path
        repo = git.Repo.init(repo_dir)

        # Create an initial commit to avoid "empty repo" errors
        readme = os.path.join(repo_dir, "README.md")
        with open(readme, "w") as f:
            f.write("# Test Repo")

        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        # Ensure we are on a main branch
        repo.git.branch("-M", "main")

        return str(repo_dir)

    @pytest.mark.asyncio
    async def test_create_checkpoint_success(self, isolated_repo: str) -> None:
        """Verifies that create_checkpoint creates a new branch in isolated repo."""
        provider = GitVersionControlProvider(repo_path=isolated_repo)
        task_id = uuid4()

        branch_name = await provider.create_checkpoint(task_id)

        repo = git.Repo(isolated_repo)
        assert branch_name in [b.name for b in repo.branches]
        assert "human-fix-checkpoint" in branch_name
        assert str(repo.active_branch) == branch_name

    @pytest.mark.asyncio
    async def test_get_diff_generation(self, isolated_repo: str) -> None:
        """Verifies diff calculation between main and checkpoint."""
        provider = GitVersionControlProvider(repo_path=isolated_repo)
        repo = git.Repo(isolated_repo)

        # 1. Create a branch and modify a file
        checkpoint_branch = await provider.create_checkpoint(uuid4())
        test_file = os.path.join(isolated_repo, "logic.py")
        with open(test_file, "w") as f:
            f.write("print('hello')")

        repo.index.add(["logic.py"])
        repo.index.commit("Agent change")

        # 2. Compare against main
        diff = await provider.get_diff("main", checkpoint_branch)

        assert "print('hello')" in diff
        assert "logic.py" in diff
