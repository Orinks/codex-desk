from __future__ import annotations

import subprocess

from codex_desk.codex_plugins import CodexPluginService


class RecordingRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def __call__(self, command, **kwargs):
        self.commands.append(list(command))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


def test_add_marketplace_command_supports_ref_and_sparse_path():
    runner = RecordingRunner()
    service = CodexPluginService(runner=runner)

    service.add_marketplace("owner/repo", ref="main", sparse="marketplace")

    assert runner.commands == [
        [
            "codex",
            "plugin",
            "marketplace",
            "add",
            "owner/repo",
            "--ref",
            "main",
            "--sparse",
            "marketplace",
        ]
    ]


def test_upgrade_marketplace_can_target_one_or_all():
    runner = RecordingRunner()
    service = CodexPluginService(runner=runner)

    service.upgrade_marketplace()
    service.upgrade_marketplace("openai-bundled")

    assert runner.commands == [
        ["codex", "plugin", "marketplace", "upgrade"],
        ["codex", "plugin", "marketplace", "upgrade", "openai-bundled"],
    ]


def test_remove_marketplace_command():
    runner = RecordingRunner()
    service = CodexPluginService(runner=runner)

    service.remove_marketplace("plugins-cli")

    assert runner.commands == [["codex", "plugin", "marketplace", "remove", "plugins-cli"]]
