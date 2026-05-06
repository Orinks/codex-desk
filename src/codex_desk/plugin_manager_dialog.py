"""Native Codex plugin and marketplace manager."""

from __future__ import annotations

import subprocess

import wx

from codex_desk.codex_config import CodexConfigService, CodexMarketplace, CodexPlugin
from codex_desk.codex_plugins import CodexPluginService


class PluginManagerDialog(wx.Dialog):
    """Manage Codex plugins and plugin marketplaces."""

    def __init__(
        self,
        parent: wx.Window,
        config_service: CodexConfigService | None = None,
        plugin_service: CodexPluginService | None = None,
    ) -> None:
        super().__init__(
            parent,
            title="Codex Plugins",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(780, 500),
        )
        self._config_service = config_service or CodexConfigService()
        self._plugin_service = plugin_service or CodexPluginService()
        self._plugins: list[CodexPlugin] = []
        self._marketplaces: list[CodexMarketplace] = []
        self._create_controls()
        self._refresh()

    def _create_controls(self) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        notebook = wx.Notebook(panel)

        plugins_panel = wx.Panel(notebook)
        plugins_sizer = wx.BoxSizer(wx.VERTICAL)
        plugins_label = wx.StaticText(plugins_panel, label="Configured plugins:")
        self._plugins_list = wx.ListCtrl(plugins_panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self._plugins_list.InsertColumn(0, "Plugin")
        self._plugins_list.InsertColumn(1, "Enabled")
        self._plugins_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_plugin_selection_changed)
        self._plugins_list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_plugin_selection_changed)

        plugin_buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._enable_plugin_button = wx.Button(plugins_panel, label="Enable")
        self._disable_plugin_button = wx.Button(plugins_panel, label="Disable")
        self._refresh_plugins_button = wx.Button(plugins_panel, label="Refresh")
        for button in (
            self._enable_plugin_button,
            self._disable_plugin_button,
            self._refresh_plugins_button,
        ):
            plugin_buttons.Add(button, flag=wx.RIGHT, border=6)
        self._enable_plugin_button.Bind(wx.EVT_BUTTON, lambda event: self._set_selected_plugin(True))
        self._disable_plugin_button.Bind(wx.EVT_BUTTON, lambda event: self._set_selected_plugin(False))
        self._refresh_plugins_button.Bind(wx.EVT_BUTTON, lambda event: self._refresh())

        plugins_sizer.Add(plugins_label, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=8)
        plugins_sizer.Add(self._plugins_list, proportion=1, flag=wx.EXPAND | wx.ALL, border=8)
        plugins_sizer.Add(plugin_buttons, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)
        plugins_panel.SetSizer(plugins_sizer)

        marketplaces_panel = wx.Panel(notebook)
        marketplace_sizer = wx.BoxSizer(wx.VERTICAL)
        marketplace_label = wx.StaticText(marketplaces_panel, label="Configured marketplaces:")
        self._marketplaces_list = wx.ListCtrl(
            marketplaces_panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL,
        )
        for index, heading in enumerate(("Name", "Source type", "Source", "Last updated")):
            self._marketplaces_list.InsertColumn(index, heading)
        self._marketplaces_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_marketplace_selection_changed)
        self._marketplaces_list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_marketplace_selection_changed)

        marketplace_buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._add_marketplace_button = wx.Button(marketplaces_panel, label="Add marketplace")
        self._upgrade_marketplace_button = wx.Button(marketplaces_panel, label="Upgrade selected")
        self._upgrade_all_marketplaces_button = wx.Button(marketplaces_panel, label="Upgrade all")
        self._remove_marketplace_button = wx.Button(marketplaces_panel, label="Remove")
        for button in (
            self._add_marketplace_button,
            self._upgrade_marketplace_button,
            self._upgrade_all_marketplaces_button,
            self._remove_marketplace_button,
        ):
            marketplace_buttons.Add(button, flag=wx.RIGHT, border=6)
        self._add_marketplace_button.Bind(wx.EVT_BUTTON, self._on_add_marketplace)
        self._upgrade_marketplace_button.Bind(wx.EVT_BUTTON, self._on_upgrade_marketplace)
        self._upgrade_all_marketplaces_button.Bind(wx.EVT_BUTTON, self._on_upgrade_all_marketplaces)
        self._remove_marketplace_button.Bind(wx.EVT_BUTTON, self._on_remove_marketplace)

        marketplace_sizer.Add(marketplace_label, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=8)
        marketplace_sizer.Add(
            self._marketplaces_list,
            proportion=1,
            flag=wx.EXPAND | wx.ALL,
            border=8,
        )
        marketplace_sizer.Add(marketplace_buttons, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)
        marketplaces_panel.SetSizer(marketplace_sizer)

        notebook.AddPage(plugins_panel, "Plugins")
        notebook.AddPage(marketplaces_panel, "Marketplaces")

        close_buttons = self.CreateSeparatedButtonSizer(wx.CLOSE)
        sizer.Add(notebook, proportion=1, flag=wx.EXPAND | wx.ALL, border=8)
        sizer.Add(close_buttons, flag=wx.EXPAND | wx.ALL, border=8)
        panel.SetSizer(sizer)

    def _refresh(self) -> None:
        self._plugins = self._config_service.list_plugins()
        self._marketplaces = self._config_service.list_marketplaces()
        self._populate_plugins()
        self._populate_marketplaces()
        self._sync_plugin_buttons()
        self._sync_marketplace_buttons()

    def _populate_plugins(self) -> None:
        self._plugins_list.DeleteAllItems()
        for plugin in self._plugins:
            index = self._plugins_list.InsertItem(self._plugins_list.GetItemCount(), plugin.plugin_id)
            self._plugins_list.SetItem(index, 1, "yes" if plugin.enabled else "no")
        for column in range(2):
            self._plugins_list.SetColumnWidth(column, wx.LIST_AUTOSIZE_USEHEADER)

    def _populate_marketplaces(self) -> None:
        self._marketplaces_list.DeleteAllItems()
        for marketplace in self._marketplaces:
            index = self._marketplaces_list.InsertItem(
                self._marketplaces_list.GetItemCount(),
                marketplace.name,
            )
            self._marketplaces_list.SetItem(index, 1, marketplace.source_type)
            self._marketplaces_list.SetItem(index, 2, marketplace.source)
            self._marketplaces_list.SetItem(index, 3, marketplace.last_updated)
        for column in range(4):
            self._marketplaces_list.SetColumnWidth(column, wx.LIST_AUTOSIZE_USEHEADER)

    def _selected_plugin(self) -> CodexPlugin | None:
        index = self._plugins_list.GetFirstSelected()
        if index == -1:
            return None
        return self._plugins[index]

    def _selected_marketplace(self) -> CodexMarketplace | None:
        index = self._marketplaces_list.GetFirstSelected()
        if index == -1:
            return None
        return self._marketplaces[index]

    def _on_plugin_selection_changed(self, event: wx.ListEvent) -> None:
        self._sync_plugin_buttons()
        event.Skip()

    def _on_marketplace_selection_changed(self, event: wx.ListEvent) -> None:
        self._sync_marketplace_buttons()
        event.Skip()

    def _sync_plugin_buttons(self) -> None:
        plugin = self._selected_plugin()
        self._enable_plugin_button.Enable(plugin is not None and not plugin.enabled)
        self._disable_plugin_button.Enable(plugin is not None and plugin.enabled)

    def _sync_marketplace_buttons(self) -> None:
        has_selection = self._selected_marketplace() is not None
        self._upgrade_marketplace_button.Enable(has_selection)
        self._remove_marketplace_button.Enable(has_selection)

    def _set_selected_plugin(self, enabled: bool) -> None:
        plugin = self._selected_plugin()
        if not plugin:
            return
        self._config_service.set_plugin_enabled(plugin.plugin_id, enabled)
        self._refresh()

    def _on_add_marketplace(self, event: wx.CommandEvent) -> None:
        dialog = AddMarketplaceDialog(self)
        try:
            if dialog.ShowModal() == wx.ID_OK:
                self._plugin_service.add_marketplace(**dialog.get_values())
                self._refresh()
        except (OSError, subprocess.CalledProcessError) as exc:
            self._show_error("Could not add plugin marketplace.", exc)
        finally:
            dialog.Destroy()

    def _on_upgrade_marketplace(self, event: wx.CommandEvent) -> None:
        marketplace = self._selected_marketplace()
        if not marketplace:
            return
        try:
            self._plugin_service.upgrade_marketplace(marketplace.name)
            self._refresh()
        except (OSError, subprocess.CalledProcessError) as exc:
            self._show_error("Could not upgrade plugin marketplace.", exc)

    def _on_upgrade_all_marketplaces(self, event: wx.CommandEvent) -> None:
        try:
            self._plugin_service.upgrade_marketplace()
            self._refresh()
        except (OSError, subprocess.CalledProcessError) as exc:
            self._show_error("Could not upgrade plugin marketplaces.", exc)

    def _on_remove_marketplace(self, event: wx.CommandEvent) -> None:
        marketplace = self._selected_marketplace()
        if not marketplace:
            return
        if wx.MessageBox(
            f"Remove plugin marketplace '{marketplace.name}'?",
            "Remove Marketplace",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        ) != wx.YES:
            return
        try:
            self._plugin_service.remove_marketplace(marketplace.name)
            self._refresh()
        except (OSError, subprocess.CalledProcessError) as exc:
            self._show_error("Could not remove plugin marketplace.", exc)

    def _show_error(self, summary: str, exc: BaseException) -> None:
        detail = str(exc)
        if isinstance(exc, subprocess.CalledProcessError):
            detail = exc.stderr or exc.stdout or str(exc)
        wx.MessageBox(f"{summary}\n\n{detail}", "Codex Plugins", wx.OK | wx.ICON_ERROR)


class AddMarketplaceDialog(wx.Dialog):
    """Collect a plugin marketplace source."""

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, title="Add Plugin Marketplace", style=wx.DEFAULT_DIALOG_STYLE)
        self._create_controls()
        self.Fit()
        self.SetMinSize(self.GetSize())

    def get_values(self) -> dict:
        return {
            "source": self._source.GetValue().strip(),
            "ref": self._ref.GetValue().strip() or None,
            "sparse": self._sparse.GetValue().strip() or None,
        }

    def _create_controls(self) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self._source = _add_labeled_text(panel, sizer, "Marketplace source:")
        self._ref = _add_labeled_text(panel, sizer, "Git ref:")
        self._sparse = _add_labeled_text(panel, sizer, "Sparse checkout path:")
        buttons = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(buttons, flag=wx.EXPAND | wx.ALL, border=8)
        panel.SetSizer(sizer)


def _add_labeled_text(panel: wx.Panel, sizer: wx.BoxSizer, label: str) -> wx.TextCtrl:
    sizer.Add(wx.StaticText(panel, label=label), flag=wx.LEFT | wx.RIGHT | wx.TOP, border=8)
    control = wx.TextCtrl(panel)
    sizer.Add(control, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)
    return control
