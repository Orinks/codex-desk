"""Native MCP server manager."""

from __future__ import annotations

import shlex
import subprocess

import wx

from wxpi.codex_mcp import CodexMcpService, McpServer


class McpManagerDialog(wx.Dialog):
    """Manage Codex MCP servers through the Codex CLI."""

    def __init__(self, parent: wx.Window, service: CodexMcpService | None = None) -> None:
        super().__init__(
            parent,
            title="MCP Servers",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(760, 460),
        )
        self._service = service or CodexMcpService()
        self._servers: list[McpServer] = []
        self._create_controls()
        self._refresh_servers()

    def _create_controls(self) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        servers_label = wx.StaticText(panel, label="Configured MCP servers:")
        self._server_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        for index, heading in enumerate(("Name", "Type", "Target", "Status", "Auth")):
            self._server_list.InsertColumn(index, heading)
        self._server_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_selection_changed)
        self._server_list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_selection_changed)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._add_stdio_button = wx.Button(panel, label="Add stdio server")
        self._add_http_button = wx.Button(panel, label="Add HTTP server")
        self._remove_button = wx.Button(panel, label="Remove")
        self._login_button = wx.Button(panel, label="Log in")
        self._logout_button = wx.Button(panel, label="Log out")
        self._refresh_button = wx.Button(panel, label="Refresh")
        for button in (
            self._add_stdio_button,
            self._add_http_button,
            self._remove_button,
            self._login_button,
            self._logout_button,
            self._refresh_button,
        ):
            button_sizer.Add(button, flag=wx.RIGHT, border=6)

        self._add_stdio_button.Bind(wx.EVT_BUTTON, self._on_add_stdio)
        self._add_http_button.Bind(wx.EVT_BUTTON, self._on_add_http)
        self._remove_button.Bind(wx.EVT_BUTTON, self._on_remove)
        self._login_button.Bind(wx.EVT_BUTTON, self._on_login)
        self._logout_button.Bind(wx.EVT_BUTTON, self._on_logout)
        self._refresh_button.Bind(wx.EVT_BUTTON, lambda event: self._refresh_servers())

        close_buttons = self.CreateSeparatedButtonSizer(wx.CLOSE)
        sizer.Add(servers_label, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=8)
        sizer.Add(self._server_list, proportion=1, flag=wx.EXPAND | wx.ALL, border=8)
        sizer.Add(button_sizer, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)
        sizer.Add(close_buttons, flag=wx.EXPAND | wx.ALL, border=8)
        panel.SetSizer(sizer)

    def _refresh_servers(self) -> None:
        try:
            self._servers = self._service.list_servers()
        except (OSError, subprocess.CalledProcessError) as exc:
            self._show_error("Could not list MCP servers.", exc)
            return

        self._server_list.DeleteAllItems()
        for server in self._servers:
            index = self._server_list.InsertItem(self._server_list.GetItemCount(), server.name)
            self._server_list.SetItem(index, 1, server.transport)
            self._server_list.SetItem(index, 2, _server_target(server))
            self._server_list.SetItem(index, 3, server.status)
            self._server_list.SetItem(index, 4, server.auth)
        for column in range(5):
            self._server_list.SetColumnWidth(column, wx.LIST_AUTOSIZE_USEHEADER)
        self._sync_buttons()

    def _selected_server(self) -> McpServer | None:
        index = self._server_list.GetFirstSelected()
        if index == -1:
            return None
        return self._servers[index]

    def _on_selection_changed(self, event: wx.ListEvent) -> None:
        self._sync_buttons()
        event.Skip()

    def _sync_buttons(self) -> None:
        has_selection = self._selected_server() is not None
        self._remove_button.Enable(has_selection)
        self._login_button.Enable(has_selection)
        self._logout_button.Enable(has_selection)

    def _on_add_stdio(self, event: wx.CommandEvent) -> None:
        dialog = AddStdioMcpServerDialog(self)
        try:
            if dialog.ShowModal() == wx.ID_OK:
                values = dialog.get_values()
                self._service.add_stdio_server(**values)
                self._refresh_servers()
        except (OSError, subprocess.CalledProcessError) as exc:
            self._show_error("Could not add stdio MCP server.", exc)
        finally:
            dialog.Destroy()

    def _on_add_http(self, event: wx.CommandEvent) -> None:
        dialog = AddHttpMcpServerDialog(self)
        try:
            if dialog.ShowModal() == wx.ID_OK:
                self._service.add_http_server(**dialog.get_values())
                self._refresh_servers()
        except (OSError, subprocess.CalledProcessError) as exc:
            self._show_error("Could not add HTTP MCP server.", exc)
        finally:
            dialog.Destroy()

    def _on_remove(self, event: wx.CommandEvent) -> None:
        server = self._selected_server()
        if not server:
            return
        if wx.MessageBox(
            f"Remove MCP server '{server.name}'?",
            "Remove MCP Server",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        ) != wx.YES:
            return
        try:
            self._service.remove_server(server.name)
            self._refresh_servers()
        except (OSError, subprocess.CalledProcessError) as exc:
            self._show_error("Could not remove MCP server.", exc)

    def _on_login(self, event: wx.CommandEvent) -> None:
        server = self._selected_server()
        if not server:
            return
        scopes = wx.GetTextFromUser(
            "Optional comma-separated OAuth scopes:",
            "MCP Login",
            parent=self,
        )
        try:
            self._service.login(server.name, scopes=_parse_scopes(scopes))
            self._refresh_servers()
        except (OSError, subprocess.CalledProcessError) as exc:
            self._show_error("Could not log in to MCP server.", exc)

    def _on_logout(self, event: wx.CommandEvent) -> None:
        server = self._selected_server()
        if not server:
            return
        try:
            self._service.logout(server.name)
            self._refresh_servers()
        except (OSError, subprocess.CalledProcessError) as exc:
            self._show_error("Could not log out of MCP server.", exc)

    def _show_error(self, summary: str, exc: BaseException) -> None:
        detail = str(exc)
        if isinstance(exc, subprocess.CalledProcessError):
            detail = exc.stderr or exc.stdout or str(exc)
        wx.MessageBox(f"{summary}\n\n{detail}", "MCP Servers", wx.OK | wx.ICON_ERROR)


class AddStdioMcpServerDialog(wx.Dialog):
    """Collect stdio MCP server details."""

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, title="Add stdio MCP Server", style=wx.DEFAULT_DIALOG_STYLE)
        self._create_controls()
        self.Fit()
        self.SetMinSize(self.GetSize())

    def get_values(self) -> dict:
        return {
            "name": self._name.GetValue().strip(),
            "command": self._command.GetValue().strip(),
            "args": shlex.split(self._args.GetValue()),
            "env": _parse_env(self._env.GetValue()),
        }

    def _create_controls(self) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self._name = _add_labeled_text(panel, sizer, "Server name:")
        self._command = _add_labeled_text(panel, sizer, "Command:")
        self._args = _add_labeled_text(panel, sizer, "Arguments:")
        self._env = _add_labeled_text(
            panel,
            sizer,
            "Environment variables, one KEY=VALUE per line:",
            style=wx.TE_MULTILINE,
        )
        buttons = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(buttons, flag=wx.EXPAND | wx.ALL, border=8)
        panel.SetSizer(sizer)


class AddHttpMcpServerDialog(wx.Dialog):
    """Collect HTTP MCP server details."""

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, title="Add HTTP MCP Server", style=wx.DEFAULT_DIALOG_STYLE)
        self._create_controls()
        self.Fit()
        self.SetMinSize(self.GetSize())

    def get_values(self) -> dict:
        return {
            "name": self._name.GetValue().strip(),
            "url": self._url.GetValue().strip(),
            "bearer_token_env_var": self._bearer_env.GetValue().strip() or None,
        }

    def _create_controls(self) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self._name = _add_labeled_text(panel, sizer, "Server name:")
        self._url = _add_labeled_text(panel, sizer, "Server URL:")
        self._bearer_env = _add_labeled_text(panel, sizer, "Bearer token environment variable:")
        buttons = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(buttons, flag=wx.EXPAND | wx.ALL, border=8)
        panel.SetSizer(sizer)


def _add_labeled_text(
    panel: wx.Panel,
    sizer: wx.BoxSizer,
    label: str,
    style: int = 0,
) -> wx.TextCtrl:
    sizer.Add(wx.StaticText(panel, label=label), flag=wx.LEFT | wx.RIGHT | wx.TOP, border=8)
    control = wx.TextCtrl(panel, style=style)
    sizer.Add(control, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)
    return control


def _parse_env(raw: str) -> dict[str, str]:
    env = {}
    for line in raw.splitlines():
        if not line.strip() or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def _parse_scopes(raw: str) -> list[str]:
    return [scope.strip() for scope in raw.split(",") if scope.strip()]


def _server_target(server: McpServer) -> str:
    if server.transport == "http":
        return server.url
    pieces = [server.command, server.args]
    return " ".join(piece for piece in pieces if piece)
