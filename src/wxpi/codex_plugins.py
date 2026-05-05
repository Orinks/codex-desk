"""Codex plugin marketplace command service."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable, Sequence

from wxpi.constants import CODEX_BINARY


Runner = Callable[..., subprocess.CompletedProcess[str]]


class CodexPluginService:
    """Subprocess wrapper around ``codex plugin marketplace``."""

    def __init__(
        self,
        *,
        runner: Runner = subprocess.run,
        codex_binary: str = CODEX_BINARY,
    ) -> None:
        self._runner = runner
        self._codex_binary = codex_binary

    def add_marketplace(
        self,
        source: str,
        *,
        ref: str | None = None,
        sparse: str | None = None,
    ) -> None:
        """Add a Codex plugin marketplace."""
        command = ["plugin", "marketplace", "add", source]
        if ref:
            command.extend(["--ref", ref])
        if sparse:
            command.extend(["--sparse", sparse])
        self._run(command)

    def upgrade_marketplace(self, name: str | None = None) -> None:
        """Upgrade one marketplace, or all marketplaces when no name is given."""
        command = ["plugin", "marketplace", "upgrade"]
        if name:
            command.append(name)
        self._run(command)

    def remove_marketplace(self, name: str) -> None:
        """Remove a configured plugin marketplace."""
        self._run(["plugin", "marketplace", "remove", name])

    def _run(self, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return self._runner(
            [self._codex_binary, *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            shell=sys.platform == "win32",
        )
