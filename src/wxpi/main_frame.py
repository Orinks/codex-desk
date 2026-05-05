"""Main window frame for wxAgent."""
from dataclasses import replace
import os
import wx

from wxpi.codex_models import load_model_choices
from wxpi.constants import APP_NAME
from wxpi.mcp_manager_dialog import McpManagerDialog
from wxpi.new_session_dialog import NewSessionDialog
from wxpi.plugin_manager_dialog import PluginManagerDialog
from wxpi.preferences import AppPreferences, REASONING_EFFORTS, ThreadOptions
from wxpi.profile_dialog import ProfileDialog
from wxpi.session_controller import SessionController
from wxpi.settings_dialog import SettingsDialog
from wxpi.worktrees import create_worktree


class MainFrame(wx.Frame):
    """Main window containing the transcript, input, and status bar."""

    def __init__(self) -> None:
        super().__init__(
            None,
            wx.ID_ANY,
            APP_NAME,
            size=(900, 700),
        )

        # Get initial working directory
        self._cwd = os.getcwd()
        self._model = ""
        self._turn_status = "Idle"
        self._preferences = AppPreferences()
        self._thread_options = ThreadOptions()

        # Create the session controller (owns PiBridge)
        self._session_controller = SessionController(self)

        # Build UI
        self._create_menu_bar()
        self._create_panels()
        self._create_status_bar()

        # Wire up keyboard shortcuts
        self._bind_shortcuts()

        # Update initial window title
        self._update_title()

    def _create_menu_bar(self) -> None:
        """Create the menu bar."""
        menubar = wx.MenuBar()

        # File menu
        file_menu = wx.Menu()
        new_session = wx.MenuItem(file_menu, wx.ID_NEW, "New Session\tCtrl+N")
        open_session = wx.MenuItem(file_menu, wx.ID_OPEN, "Open Session\tCtrl+O")
        change_workspace = wx.MenuItem(
            file_menu, wx.ID_ANY, "Change Workspace\tCtrl+Shift+O"
        )
        file_menu.Append(new_session)
        file_menu.Append(open_session)
        file_menu.AppendSeparator()
        file_menu.Append(change_workspace)
        file_menu.AppendSeparator()
        quit_item = wx.MenuItem(file_menu, wx.ID_EXIT, "Quit\tCtrl+Q")
        file_menu.Append(quit_item)

        self.Bind(wx.EVT_MENU, self._on_new_session, new_session)
        self.Bind(wx.EVT_MENU, self._on_open_session, open_session)
        self.Bind(wx.EVT_MENU, self._on_change_workspace, change_workspace)
        self.Bind(wx.EVT_MENU, self._on_quit, quit_item)

        # Edit menu
        edit_menu = wx.Menu()
        copy_item = wx.MenuItem(edit_menu, wx.ID_COPY, "Copy\tCtrl+C")
        edit_menu.Append(copy_item)
        self.Bind(wx.EVT_MENU, self._on_copy, copy_item)
        
        profiles_item = wx.MenuItem(edit_menu, wx.ID_ANY, "Agent Profiles...\tCtrl+P")
        edit_menu.Append(profiles_item)
        self.Bind(wx.EVT_MENU, self._on_manage_profiles, profiles_item)

        settings_item = wx.MenuItem(edit_menu, wx.ID_PREFERENCES, "Settings...\tCtrl+,")
        edit_menu.Append(settings_item)
        self.Bind(wx.EVT_MENU, self._on_settings, settings_item)

        # Help menu
        help_menu = wx.Menu()
        about_item = wx.MenuItem(help_menu, wx.ID_ABOUT, "About")
        help_menu.Append(about_item)
        self.Bind(wx.EVT_MENU, self._on_about, about_item)

        menubar.Append(file_menu, "File")
        menubar.Append(edit_menu, "Edit")
        tools_menu = wx.Menu()
        plugins_item = wx.MenuItem(tools_menu, wx.ID_ANY, "Codex Plugins...\tCtrl+Shift+P")
        mcp_servers_item = wx.MenuItem(tools_menu, wx.ID_ANY, "MCP Servers...\tCtrl+M")
        self._id_plugins = plugins_item.GetId()
        self._id_mcp_servers = mcp_servers_item.GetId()
        tools_menu.Append(plugins_item)
        tools_menu.Append(mcp_servers_item)
        self.Bind(wx.EVT_MENU, self._on_plugins, plugins_item)
        self.Bind(wx.EVT_MENU, self._on_mcp_servers, mcp_servers_item)
        menubar.Append(tools_menu, "Tools")
        menubar.Append(help_menu, "Help")

        self.SetMenuBar(menubar)

    def _create_panels(self) -> None:
        """Create the main panel layout."""
        # Main panel holds transcript and input
        main_panel = wx.Panel(self, wx.ID_ANY)
        sizer = wx.BoxSizer(wx.VERTICAL)
        session_sizer = wx.BoxSizer(wx.HORIZONTAL)

        model_label = wx.StaticText(main_panel, label="Model:")
        self._model_choice = wx.ComboBox(
            main_panel,
            choices=load_model_choices(),
            style=wx.CB_DROPDOWN,
        )
        self._model_choice.SetValue(self._thread_options.model)
        self._model_choice.Bind(wx.EVT_COMBOBOX, self._on_model_changed)
        self._model_choice.Bind(wx.EVT_TEXT, self._on_model_changed)

        reasoning_label = wx.StaticText(main_panel, label="Reasoning effort:")
        self._reasoning_choice = wx.Choice(main_panel, choices=list(REASONING_EFFORTS))
        self._reasoning_choice.SetStringSelection(self._thread_options.reasoning_effort)
        self._reasoning_choice.Bind(wx.EVT_CHOICE, self._on_reasoning_changed)

        session_sizer.Add(model_label, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=4)
        session_sizer.Add(self._model_choice, proportion=1, flag=wx.RIGHT, border=12)
        session_sizer.Add(reasoning_label, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=4)
        session_sizer.Add(self._reasoning_choice, flag=wx.RIGHT, border=4)

        transcript_label = wx.StaticText(main_panel, label="Conversation transcript:")
        self._transcript = wx.TextCtrl(
            main_panel,
            wx.ID_ANY,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
        )
        self._transcript.SetToolTip("Conversation transcript")
        # Set monospace font for transcript
        font = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName="Courier New")
        self._transcript.SetFont(font)

        prompt_label = wx.StaticText(main_panel, label="Prompt:")
        self._input = wx.TextCtrl(
            main_panel,
            wx.ID_ANY,
            style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER,
        )
        self._input.SetToolTip("Message input")
        # Set initial hint text
        self._input.SetHint("Enter your prompt... (Enter to send, Shift+Enter for new line)")

        # Bind input events
        self.Bind(wx.EVT_TEXT_ENTER, self._on_submit_prompt, self._input)

        sizer.Add(session_sizer, flag=wx.EXPAND | wx.ALL, border=4)
        sizer.Add(transcript_label, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=4)
        sizer.Add(self._transcript, proportion=8, flag=wx.EXPAND)
        sizer.Add(prompt_label, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=4)
        sizer.Add(self._input, proportion=2, flag=wx.EXPAND | wx.ALL, border=4)

        main_panel.SetSizer(sizer)

        # Give focus to input field
        self._input.SetFocus()

    def _create_status_bar(self) -> None:
        """Create the status bar."""
        self.CreateStatusBar(3)
        self._update_status_bar()

    def _update_status_bar(self) -> None:
        """Update status bar fields."""
        self.SetStatusText(self._cwd, 0)  # Working directory
        self.SetStatusText(self._model or "No model", 1)  # Model name
        self.SetStatusText(self._turn_status, 2)  # Turn status

    def _update_title(self) -> None:
        """Update window title with working directory."""
        title = f"{APP_NAME} — {self._cwd}"
        if self._model:
            title += f" — {self._model}"
        self.SetTitle(title)

    def _bind_shortcuts(self) -> None:
        """Bind keyboard shortcuts."""
        # Create menu IDs for shortcuts that don't have menu items
        self._id_change_workspace = wx.NewId()
        self._id_abort = wx.NewId()
        
        accel = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('N'), wx.ID_NEW),
            (wx.ACCEL_CTRL, ord('O'), wx.ID_OPEN),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('O'), self._id_change_workspace),
            (wx.ACCEL_CTRL, ord('M'), self._id_mcp_servers),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('P'), self._id_plugins),
            (wx.ACCEL_CTRL, ord('Q'), wx.ID_EXIT),
            (wx.ACCEL_NORMAL, wx.WXK_ESCAPE, self._id_abort),
        ])
        self.SetAcceleratorTable(accel)
        
        # Bind the new IDs
        self.Bind(wx.EVT_MENU, self._on_change_workspace, id=self._id_change_workspace)
        self.Bind(wx.EVT_MENU, self._on_abort, id=self._id_abort)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_submit_prompt(self, event: wx.CommandEvent) -> None:
        """Handle prompt submission."""
        text = self._input.GetValue().strip()
        if not text:
            return
        self._session_controller.send_prompt(text)
        self._input.Clear()

    def _on_model_changed(self, event: wx.CommandEvent) -> None:
        """Update the model for future turns."""
        model = self._model_choice.GetValue().strip()
        if model:
            self._thread_options = replace(self._thread_options, model=model)
            self._session_controller.set_thread_options(self._thread_options)
            self.set_model(model)
        event.Skip()

    def _on_reasoning_changed(self, event: wx.CommandEvent) -> None:
        """Update reasoning effort for future turns."""
        reasoning = self._reasoning_choice.GetStringSelection()
        if reasoning:
            self._thread_options = replace(self._thread_options, reasoning_effort=reasoning)
            self._session_controller.set_thread_options(self._thread_options)
        event.Skip()

    def _on_new_session(self, event: wx.CommandEvent) -> None:
        """Start a new session."""
        dlg = NewSessionDialog(self, self._cwd, self._thread_options)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self._start_configured_session(dlg.get_cwd(), dlg.get_thread_options())
        finally:
            dlg.Destroy()

    def _on_open_session(self, event: wx.CommandEvent) -> None:
        """Open an existing session."""
        default_dir = os.path.expanduser("~/.pi/agent/sessions/")
        dlg = wx.FileDialog(
            self,
            "Choose a session file:",
            defaultDir=default_dir,
            wildcard="Session files (*.jsonl)|*.jsonl",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        if dlg.ShowModal() == wx.ID_OK:
            session_path = dlg.GetPath()
            # Extract working directory from session file path
            self._cwd = os.path.dirname(os.path.dirname(session_path))
            self._update_title()
            self._update_status_bar()
            self._session_controller.continue_session(session_path)

    def _on_change_workspace(self, event: wx.CommandEvent) -> None:
        """Change the working directory."""
        dlg = NewSessionDialog(self, self._cwd, self._thread_options)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self._start_configured_session(dlg.get_cwd(), dlg.get_thread_options())
        finally:
            dlg.Destroy()

    def _on_quit(self, event: wx.CommandEvent) -> None:
        """Quit the application."""
        self.Close()

    def _on_abort(self, event: wx.CommandEvent) -> None:
        """Abort the current operation (Escape key)."""
        self._session_controller.send_abort()

    def _on_copy(self, event: wx.CommandEvent) -> None:
        """Copy selected text."""
        if self._input.HasFocus():
            self._input.Copy()
        elif self._transcript.HasFocus():
            self._transcript.Copy()

    def _on_manage_profiles(self, event: wx.CommandEvent) -> None:
        """Open profile management dialog."""
        dlg = ProfileDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

    def _on_mcp_servers(self, event: wx.CommandEvent) -> None:
        """Open MCP server management dialog."""
        dlg = McpManagerDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

    def _on_plugins(self, event: wx.CommandEvent) -> None:
        """Open Codex plugin management dialog."""
        dlg = PluginManagerDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

    def _on_settings(self, event: wx.CommandEvent) -> None:
        """Open app settings."""
        dlg = SettingsDialog(self, self._preferences)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self._preferences = dlg.get_preferences()
                self._session_controller.set_preferences(self._preferences)
        finally:
            dlg.Destroy()

    def _on_about(self, event: wx.CommandEvent) -> None:
        """Show about dialog."""
        wx.MessageBox(
            f"{APP_NAME}\n\n"
            "A native accessible wxPython frontend for Codex.\n\n"
            "Built with wxPython.",
            f"About {APP_NAME}",
            wx.OK | wx.ICON_INFORMATION,
        )

    def _start_configured_session(self, cwd: str, options: ThreadOptions) -> None:
        """Start a local or worktree-backed Codex session."""
        session_cwd = cwd
        if options.mode == "worktree":
            try:
                worktree = create_worktree(cwd, options.base_branch or "HEAD")
            except Exception as exc:
                wx.MessageBox(
                    f"Could not create Git worktree:\n\n{exc}",
                    "New Session",
                    wx.OK | wx.ICON_ERROR,
                )
                return
            session_cwd = str(worktree.path)

        self._cwd = session_cwd
        self._thread_options = options
        self._model_choice.SetValue(options.model)
        self._reasoning_choice.SetStringSelection(options.reasoning_effort)
        self._update_title()
        self._update_status_bar()
        self._session_controller.new_session(
            self._cwd,
            preferences=self._preferences,
            thread_options=self._thread_options,
        )

    # ------------------------------------------------------------------
    # Public API for SessionController
    # ------------------------------------------------------------------

    def append_transcript(self, text: str) -> None:
        """Append text to the transcript."""
        # Must use CallAfter since this may be called from background thread
        wx.CallAfter(self._transcript.AppendText, text)

    def set_turn_status(self, status: str) -> None:
        """Update the turn status in the status bar."""
        self._turn_status = status
        wx.CallAfter(self._update_status_bar)

    def set_model(self, model: str) -> None:
        """Update the model name in the status bar and title."""
        self._model = model
        wx.CallAfter(self._update_title)
        wx.CallAfter(self._update_status_bar)

    def get_input_focus(self) -> None:
        """Set focus to the input field."""
        wx.CallAfter(self._input.SetFocus)
