"""Safe read/write helpers for Codex config.toml."""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile


@dataclass(frozen=True)
class CodexMarketplace:
    """Configured Codex plugin marketplace."""

    name: str
    source_type: str
    source: str
    last_updated: str = ""


@dataclass(frozen=True)
class CodexPlugin:
    """Configured Codex plugin entry."""

    plugin_id: str
    enabled: bool


class CodexConfigService:
    """Read and update the user's Codex config without owning unrelated settings."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path or self.default_config_path()

    @property
    def config_path(self) -> Path:
        """Return the active config path."""
        return self._config_path

    @staticmethod
    def default_config_path() -> Path:
        """Return the config path Codex uses by default."""
        codex_home = os.environ.get("CODEX_HOME")
        if codex_home:
            return Path(codex_home) / "config.toml"
        return Path.home() / ".codex" / "config.toml"

    def list_marketplaces(self) -> list[CodexMarketplace]:
        """Return configured plugin marketplaces."""
        data = self._load()
        marketplaces = data.get("marketplaces", {})
        if not isinstance(marketplaces, dict):
            return []
        result = []
        for name, values in marketplaces.items():
            if not isinstance(values, dict):
                continue
            result.append(
                CodexMarketplace(
                    name=str(name),
                    source_type=str(values.get("source_type", "")),
                    source=str(values.get("source", "")),
                    last_updated=str(values.get("last_updated", "")),
                )
            )
        return result

    def list_plugins(self) -> list[CodexPlugin]:
        """Return configured Codex plugins."""
        data = self._load()
        plugins = data.get("plugins", {})
        if not isinstance(plugins, dict):
            return []
        result = []
        for plugin_id, values in plugins.items():
            if not isinstance(values, dict):
                continue
            result.append(CodexPlugin(plugin_id=str(plugin_id), enabled=bool(values.get("enabled"))))
        return result

    def set_plugin_enabled(self, plugin_id: str, enabled: bool) -> None:
        """Enable or disable a plugin entry, preserving unrelated config text."""
        text = self._read_text()
        updated = _upsert_plugin_enabled(text, plugin_id, enabled)
        self._write_text(updated)

    def _load(self) -> dict:
        if not self._config_path.exists():
            return {}
        try:
            return tomllib.loads(self._config_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            return {}

    def _read_text(self) -> str:
        if not self._config_path.exists():
            return ""
        return self._config_path.read_text(encoding="utf-8")

    def _write_text(self, text: str) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        if self._config_path.exists():
            backup_path = self._config_path.with_suffix(self._config_path.suffix + ".bak")
            backup_path.write_text(self._config_path.read_text(encoding="utf-8"), encoding="utf-8")

        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            dir=str(self._config_path.parent),
            newline="\n",
        ) as stream:
            stream.write(text)
            temp_path = Path(stream.name)
        temp_path.replace(self._config_path)


def _upsert_plugin_enabled(text: str, plugin_id: str, enabled: bool) -> str:
    escaped_plugin_id = plugin_id.replace("\\", "\\\\").replace('"', '\\"')
    header = f'[plugins."{escaped_plugin_id}"]'
    enabled_line = f"enabled = {str(enabled).lower()}"
    lines = text.splitlines()

    header_index = _find_line(lines, header)
    if header_index is None:
        prefix = text.rstrip("\n")
        separator = "\n\n" if prefix else ""
        return f"{prefix}{separator}{header}\n{enabled_line}\n"

    next_header_index = _find_next_header(lines, header_index + 1)
    enabled_index = _find_enabled_line(lines, header_index + 1, next_header_index)
    if enabled_index is not None:
        lines[enabled_index] = enabled_line
    else:
        lines.insert(next_header_index, enabled_line)
    return "\n".join(lines) + "\n"


def _find_line(lines: list[str], text: str) -> int | None:
    for index, line in enumerate(lines):
        if line.strip() == text:
            return index
    return None


def _find_next_header(lines: list[str], start: int) -> int:
    for index in range(start, len(lines)):
        if re.match(r"\s*\[.+\]\s*$", lines[index]):
            return index
    return len(lines)


def _find_enabled_line(lines: list[str], start: int, end: int) -> int | None:
    for index in range(start, end):
        if re.match(r"\s*enabled\s*=", lines[index]):
            return index
    return None
