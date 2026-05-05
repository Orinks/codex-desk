"""Git worktree helpers for isolated Codex threads."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorktreeInfo:
    """Created worktree metadata."""

    path: Path
    base_branch: str


def list_branches(repo_path: str) -> list[str]:
    """Return local and remote branch names for a Git repository."""
    active_branch = current_branch(repo_path)
    result = subprocess.run(
        ["git", "branch", "--all", "--format=%(refname:short)"],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    branches = []
    for line in result.stdout.splitlines():
        branch = line.strip()
        if not branch or branch == "HEAD":
            continue
        if branch.startswith("remotes/"):
            branch = branch.removeprefix("remotes/")
        if branch not in branches:
            branches.append(branch)
    if active_branch in branches:
        branches.remove(active_branch)
        branches.insert(0, active_branch)
    return branches


def current_branch(repo_path: str) -> str:
    """Return the current Git branch, or HEAD when detached."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip() or "HEAD"


def create_worktree(repo_path: str, base_branch: str, codex_home: str | None = None) -> WorktreeInfo:
    """Create a detached Codex-style worktree for a thread."""
    root = _repo_root(repo_path)
    worktrees_root = _worktrees_root(codex_home)
    worktrees_root.mkdir(parents=True, exist_ok=True)
    target = _unique_worktree_path(worktrees_root, root.name, base_branch)
    subprocess.run(
        ["git", "worktree", "add", "--detach", str(target), base_branch],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return WorktreeInfo(path=target, base_branch=base_branch)


def _repo_root(repo_path: str) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return Path(result.stdout.strip())


def _worktrees_root(codex_home: str | None) -> Path:
    if codex_home:
        return Path(codex_home) / "worktrees"
    return Path.home() / ".codex" / "worktrees"


def _unique_worktree_path(root: Path, repo_name: str, base_branch: str) -> Path:
    safe_branch = re.sub(r"[^A-Za-z0-9._-]+", "-", base_branch).strip("-") or "head"
    prefix = f"{repo_name}-{safe_branch}"
    candidate = root / prefix
    counter = 2
    while candidate.exists():
        candidate = root / f"{prefix}-{counter}"
        counter += 1
    return candidate
