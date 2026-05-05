from __future__ import annotations

import subprocess

from wxpi.codex_mcp import CodexMcpService, McpServer


class RecordingRunner:
    def __init__(self, stdout: str = "") -> None:
        self.stdout = stdout
        self.commands: list[list[str]] = []

    def __call__(self, command, **kwargs):
        self.commands.append(list(command))
        return subprocess.CompletedProcess(command, 0, stdout=self.stdout, stderr="")


def test_list_servers_parses_codex_mcp_table():
    output = """
Name             Command  Args                       Env  Cwd       Status   Auth
a11y-agent-team  node     C:\\mcp\\stdio.js           -    C:\\mcp    enabled  Unsupported

Name    Url                     Bearer Token Env Var  Status   Auth
vercel  https://mcp.vercel.com  VERCEL_TOKEN          enabled  Not logged in
""".strip()

    service = CodexMcpService(runner=RecordingRunner(output))

    assert service.list_servers() == [
        McpServer(
            name="a11y-agent-team",
            transport="stdio",
            command="node",
            args="C:\\mcp\\stdio.js",
            env="-",
            cwd="C:\\mcp",
            status="enabled",
            auth="Unsupported",
        ),
        McpServer(
            name="vercel",
            transport="http",
            url="https://mcp.vercel.com",
            bearer_token_env_var="VERCEL_TOKEN",
            status="enabled",
            auth="Not logged in",
        ),
    ]


def test_add_stdio_server_uses_codex_mcp_add_shape():
    runner = RecordingRunner()
    service = CodexMcpService(runner=runner)

    service.add_stdio_server(
        name="docs",
        command="node",
        args=["server.js"],
        env={"TOKEN": "SECRET_ENV"},
    )

    assert runner.commands == [
        ["codex", "mcp", "add", "docs", "--env", "TOKEN=SECRET_ENV", "--", "node", "server.js"]
    ]


def test_add_http_server_uses_codex_mcp_add_shape():
    runner = RecordingRunner()
    service = CodexMcpService(runner=runner)

    service.add_http_server("vercel", "https://mcp.vercel.com", "VERCEL_TOKEN")

    assert runner.commands == [
        [
            "codex",
            "mcp",
            "add",
            "vercel",
            "--url",
            "https://mcp.vercel.com",
            "--bearer-token-env-var",
            "VERCEL_TOKEN",
        ]
    ]


def test_remove_login_logout_commands():
    runner = RecordingRunner()
    service = CodexMcpService(runner=runner)

    service.remove_server("vercel")
    service.login("vercel", scopes=["read", "write"])
    service.logout("vercel")

    assert runner.commands == [
        ["codex", "mcp", "remove", "vercel"],
        ["codex", "mcp", "login", "vercel", "--scopes", "read,write"],
        ["codex", "mcp", "logout", "vercel"],
    ]
