from __future__ import annotations

from pathlib import Path

from wxpi.codex_config import CodexConfigService


def test_lists_codex_marketplaces_and_plugins(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[marketplaces.openai-bundled]
last_updated = "2026-05-05T15:33:00Z"
source_type = "local"
source = "C:/codex/bundled"

[plugins."browser-use@openai-bundled"]
enabled = true

[plugins."vercel-plugin@plugins-cli"]
enabled = false
""".strip(),
        encoding="utf-8",
    )

    service = CodexConfigService(config_path=config_path)

    assert service.list_marketplaces()[0].name == "openai-bundled"
    assert service.list_marketplaces()[0].source == "C:/codex/bundled"
    assert service.list_plugins()[0].plugin_id == "browser-use@openai-bundled"
    assert service.list_plugins()[0].enabled is True
    assert service.list_plugins()[1].enabled is False


def test_set_plugin_enabled_updates_existing_section_and_creates_backup(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[plugins."browser-use@openai-bundled"]
enabled = true
""".strip(),
        encoding="utf-8",
    )

    service = CodexConfigService(config_path=config_path)
    service.set_plugin_enabled("browser-use@openai-bundled", False)

    assert "[plugins.\"browser-use@openai-bundled\"]" in config_path.read_text(encoding="utf-8")
    assert "enabled = false" in config_path.read_text(encoding="utf-8")
    assert (tmp_path / "config.toml.bak").exists()


def test_set_plugin_enabled_appends_missing_section(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text("model = \"gpt-5.5\"\n", encoding="utf-8")

    service = CodexConfigService(config_path=config_path)
    service.set_plugin_enabled("example@local", True)

    assert config_path.read_text(encoding="utf-8").endswith(
        '\n[plugins."example@local"]\nenabled = true\n'
    )


def test_default_config_path_points_at_codex_home(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex-home"))

    assert CodexConfigService.default_config_path() == Path(tmp_path / "codex-home" / "config.toml")
