from __future__ import annotations

import subprocess

from wxpi.worktrees import create_worktree, current_branch, list_branches


def _git(repo: str, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def test_git_worktree_helpers_create_thread_workspace(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(str(repo), "init", "-b", "main")
    (repo / "README.md").write_text("# Test\n", encoding="utf-8")
    _git(str(repo), "add", "README.md")
    _git(
        str(repo),
        "-c",
        "user.email=test@example.com",
        "-c",
        "user.name=Test User",
        "commit",
        "-m",
        "init",
    )
    _git(str(repo), "branch", "dev")

    assert current_branch(str(repo)) == "main"
    assert list_branches(str(repo)) == ["main", "dev"]

    worktree = create_worktree(str(repo), "dev", codex_home=str(tmp_path / "codex-home"))

    assert worktree.base_branch == "dev"
    assert worktree.path.exists()
    assert (worktree.path / "README.md").read_text(encoding="utf-8") == "# Test\n"
