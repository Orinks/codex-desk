"""Codex MCP command service."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from wxpi.constants import CODEX_BINARY


Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class McpServer:
    """MCP server entry reported by Codex."""

    name: str
    transport: str
    status: str
    auth: str
    command: str = ""
    args: str = ""
    env: str = ""
    cwd: str = ""
    url: str = ""
    bearer_token_env_var: str = ""


class CodexMcpService:
    """Small subprocess wrapper around ``codex mcp``."""

    def __init__(
        self,
        *,
        runner: Runner = subprocess.run,
        codex_binary: str = CODEX_BINARY,
    ) -> None:
        self._runner = runner
        self._codex_binary = codex_binary

    def list_servers(self) -> list[McpServer]:
        """Return configured MCP servers."""
        result = self._run(["mcp", "list"])
        return _parse_mcp_list(result.stdout)

    def add_stdio_server(
        self,
        *,
        name: str,
        command: str,
        args: Sequence[str] = (),
        env: dict[str, str] | None = None,
    ) -> None:
        """Add a stdio MCP server."""
        command_line = ["mcp", "add", name]
        for key, value in (env or {}).items():
            command_line.extend(["--env", f"{key}={value}"])
        command_line.extend(["--", command, *args])
        self._run(command_line)

    def add_http_server(
        self,
        name: str,
        url: str,
        bearer_token_env_var: str | None = None,
    ) -> None:
        """Add a streamable HTTP MCP server."""
        command_line = ["mcp", "add", name, "--url", url]
        if bearer_token_env_var:
            command_line.extend(["--bearer-token-env-var", bearer_token_env_var])
        self._run(command_line)

    def remove_server(self, name: str) -> None:
        """Remove an MCP server."""
        self._run(["mcp", "remove", name])

    def login(self, name: str, scopes: Sequence[str] = ()) -> None:
        """Start Codex MCP OAuth login."""
        command_line = ["mcp", "login", name]
        if scopes:
            command_line.extend(["--scopes", ",".join(scopes)])
        self._run(command_line)

    def logout(self, name: str) -> None:
        """Remove Codex MCP auth for a server."""
        self._run(["mcp", "logout", name])

    def _run(self, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return self._runner(
            [self._codex_binary, *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            shell=sys.platform == "win32",
        )


def _parse_mcp_list(output: str) -> list[McpServer]:
    servers = []
    mode = ""
    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line.startswith("Name") and "Command" in line:
            mode = "stdio"
            continue
        if line.startswith("Name") and "Url" in line:
            mode = "http"
            continue
        if mode == "stdio":
            servers.append(_parse_stdio_line(line))
        elif mode == "http":
            servers.append(_parse_http_line(line))
    return servers


def _parse_stdio_line(line: str) -> McpServer:
    parts = line.split()
    name = parts[0] if len(parts) > 0 else ""
    command = parts[1] if len(parts) > 1 else ""
    status = parts[-2] if len(parts) > 2 else ""
    auth = " ".join(parts[-1:]) if len(parts) > 2 else ""
    middle = parts[2:-2]
    cwd_index = _last_path_index(middle)
    if cwd_index is None:
        args = " ".join(middle[:-1]) if len(middle) > 1 else ""
        env = middle[-1] if middle else ""
        cwd = ""
    else:
        args = " ".join(middle[: max(cwd_index - 1, 0)])
        env = middle[cwd_index - 1] if cwd_index > 0 else ""
        cwd = " ".join(middle[cwd_index:])
    return McpServer(
        name=name,
        transport="stdio",
        command=command,
        args=args,
        env=env,
        cwd=cwd,
        status=status,
        auth=auth,
    )


def _parse_http_line(line: str) -> McpServer:
    parts = line.split()
    name = parts[0] if len(parts) > 0 else ""
    url = parts[1] if len(parts) > 1 else ""
    bearer = parts[2] if len(parts) > 2 else ""
    status = parts[3] if len(parts) > 3 else ""
    auth = " ".join(parts[4:]) if len(parts) > 4 else ""
    return McpServer(
        name=name,
        transport="http",
        url=url,
        bearer_token_env_var=bearer,
        status=status,
        auth=auth,
    )


def _last_path_index(parts: Sequence[str]) -> int | None:
    for index in range(len(parts) - 1, -1, -1):
        part = parts[index]
        if part == "-" or ":\\" in part or part.startswith("/"):
            return index
    return None
