"""Accessible slash command palette dialog."""

from __future__ import annotations

import wx

from wxpi.slash_commands import SlashCommand, filter_slash_commands


class SlashCommandDialog(wx.Dialog):
    """Native command palette for wxAgent slash commands."""

    def __init__(self, parent: wx.Window, commands: tuple[SlashCommand, ...]) -> None:
        super().__init__(
            parent,
            title="Slash Commands",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(640, 460),
        )
        self._commands = commands
        self._matches: list[SlashCommand] = list(commands)
        self._selected_command: SlashCommand | None = self._matches[0] if self._matches else None
        self._mode = "run"
        self._create_controls()
        self._populate_list()
        self.CentreOnParent()

    def get_selected_command(self) -> SlashCommand | None:
        return self._selected_command

    def should_insert(self) -> bool:
        return self._mode == "insert"

    def _create_controls(self) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        search_label = wx.StaticText(panel, label="Command search:")
        self._search = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self._search.SetToolTip("Command search")
        self._search.SetHint("Type a command name, for example /settings")
        self._search.Bind(wx.EVT_TEXT, self._on_search_changed)
        self._search.Bind(wx.EVT_TEXT_ENTER, self._on_run)

        list_label = wx.StaticText(panel, label="Slash commands:")
        self._list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self._list.SetToolTip("Slash commands")
        self._list.AppendColumn("Command", width=140)
        self._list.AppendColumn("Description", width=430)
        self._list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_run)

        details_label = wx.StaticText(panel, label="Command details:")
        self._details = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            size=(-1, 96),
        )
        self._details.SetToolTip("Command details")

        button_sizer = wx.StdDialogButtonSizer()
        self._run_button = wx.Button(panel, wx.ID_OK, "Run")
        self._insert_button = wx.Button(panel, wx.ID_ANY, "Insert")
        cancel_button = wx.Button(panel, wx.ID_CANCEL, "Cancel")
        self._run_button.Bind(wx.EVT_BUTTON, self._on_run)
        self._insert_button.Bind(wx.EVT_BUTTON, self._on_insert)
        button_sizer.AddButton(self._run_button)
        button_sizer.AddButton(self._insert_button)
        button_sizer.AddButton(cancel_button)
        button_sizer.Realize()

        sizer.Add(search_label, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=8)
        sizer.Add(self._search, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)
        sizer.Add(list_label, flag=wx.LEFT | wx.RIGHT, border=8)
        sizer.Add(self._list, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)
        sizer.Add(details_label, flag=wx.LEFT | wx.RIGHT, border=8)
        sizer.Add(self._details, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)
        sizer.Add(button_sizer, flag=wx.EXPAND | wx.ALL, border=8)
        panel.SetSizer(sizer)
        self._search.SetFocus()

    def _populate_list(self) -> None:
        self._list.DeleteAllItems()
        for index, command in enumerate(self._matches):
            self._list.InsertItem(index, command.name)
            self._list.SetItem(index, 1, command.summary)
        if self._matches:
            self._select_index(0)
            self._run_button.Enable(True)
            self._insert_button.Enable(True)
        else:
            self._selected_command = None
            self._details.ChangeValue("No matching slash commands.")
            self._run_button.Enable(False)
            self._insert_button.Enable(False)

    def _select_index(self, index: int) -> None:
        self._list.SetItemState(index, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
        self._list.EnsureVisible(index)
        self._selected_command = self._matches[index]
        self._update_details()

    def _update_details(self) -> None:
        if not self._selected_command:
            return
        command = self._selected_command
        aliases = ", ".join(command.aliases) if command.aliases else "None"
        self._details.ChangeValue(
            f"{command.name}\n\n"
            f"{command.summary}\n\n"
            f"Usage: {command.usage}\n"
            f"Aliases: {aliases}"
        )

    def _on_search_changed(self, event: wx.CommandEvent) -> None:
        self._matches = filter_slash_commands(self._search.GetValue(), self._commands)
        self._populate_list()

    def _on_select(self, event: wx.ListEvent) -> None:
        index = event.GetIndex()
        if 0 <= index < len(self._matches):
            self._selected_command = self._matches[index]
            self._update_details()

    def _on_run(self, event: wx.Event) -> None:
        if not self._selected_command:
            return
        self._mode = "run"
        self.EndModal(wx.ID_OK)

    def _on_insert(self, event: wx.Event) -> None:
        if not self._selected_command:
            return
        self._mode = "insert"
        self.EndModal(wx.ID_OK)
