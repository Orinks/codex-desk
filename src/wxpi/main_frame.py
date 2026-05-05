"""Main window frame for wxAgent."""
from dataclasses import replace
import os
import threading
import time
import wx

from wxpi.codex_models import (
    default_reasoning_effort_for_model,
    load_model_choices,
    reasoning_efforts_for_model,
)
from wxpi.constants import APP_NAME
from wxpi.mcp_manager_dialog import McpManagerDialog
from wxpi.new_session_dialog import NewSessionDialog
from wxpi.plugin_manager_dialog import PluginManagerDialog
from wxpi.preferences import AppPreferences, ThreadOptions
from wxpi.profile_dialog import ProfileDialog
from wxpi.session_controller import SessionController
from wxpi.settings_dialog import SettingsDialog
from wxpi.working_status import format_working_status
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
        self._working_started_at: float | None = None
        self._pending_prompt = False
        self._turn_details = "No turn yet"

        # Create the session controller (owns PiBridge)
        self._session_controller = SessionController(self)

        # Build UI
        self._create_menu_bar()
        self._create_panels()
        self._create_status_bar()

        # Wire up keyboard shortcuts
        self._bind_shortcuts()
        self._working_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_working_timer, self._working_timer)

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
        model_choices = _model_choices_with_current(self._thread_options.model)
        self._model_choice = wx.Choice(main_panel, choices=model_choices)
        self._model_choice.SetStringSelection(self._thread_options.model)
        self._model_choice.Bind(wx.EVT_CHOICE, self._on_model_changed)

        reasoning_label = wx.StaticText(main_panel, label="Reasoning effort:")
        self._reasoning_choice = wx.Choice(main_panel)
        self._set_reasoning_choices_for_model(
            self._thread_options.model,
            self._thread_options.reasoning_effort,
        )
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

        turn_status_sizer = wx.BoxSizer(wx.HORIZONTAL)
        turn_status_label = wx.StaticText(main_panel, label="Turn status:")
        self._turn_status_text = wx.StaticText(main_panel, label=self._turn_status)
        turn_details_label = wx.StaticText(main_panel, label="Turn details:")
        self._turn_details_text = wx.StaticText(main_panel, label=self._turn_details)
        self._working_gauge = wx.Gauge(main_panel, range=100, size=(160, -1))
        self._working_gauge.SetValue(0)
        turn_status_sizer.Add(turn_status_label, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=4)
        turn_status_sizer.Add(
            self._turn_status_text,
            proportion=1,
            flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            border=8,
        )
        turn_status_sizer.Add(self._working_gauge, flag=wx.ALIGN_CENTER_VERTICAL)
        turn_details_sizer = wx.BoxSizer(wx.HORIZONTAL)
        turn_details_sizer.Add(turn_details_label, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=4)
        turn_details_sizer.Add(self._turn_details_text, proportion=1, flag=wx.ALIGN_CENTER_VERTICAL)

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
        sizer.Add(turn_status_sizer, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=4)
        sizer.Add(turn_details_sizer, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=4)
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
        if hasattr(self, "_turn_status_text"):
            self._turn_status_text.SetLabel(self._turn_status)
        if hasattr(self, "_turn_details_text"):
            self._turn_details_text.SetLabel(self._turn_details)

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
        if not self._session_controller.has_active_session():
            if self._pending_prompt:
                self.set_turn_status("Still starting Codex")
                return
        self._input.Clear()
        self.start_working_status()
        if not self._session_controller.has_active_session():
            self._pending_prompt = True
            threading.Thread(
                target=self._start_default_session_and_send_prompt,
                args=(text,),
                daemon=True,
                name="wxagent-session-start",
            ).start()
            return
        self._session_controller.send_prompt(text)

    def _on_model_changed(self, event: wx.CommandEvent) -> None:
        """Update the model for future turns."""
        model = self._model_choice.GetStringSelection().strip()
        if model:
            reasoning = self._select_supported_reasoning_effort(
                model,
                self._thread_options.reasoning_effort,
            )
            self._set_reasoning_choices_for_model(model, reasoning)
            self._thread_options = replace(
                self._thread_options,
                model=model,
                reasoning_effort=reasoning,
            )
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
        self.stop_working_status("Idle")

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
        if self._model_choice.FindString(options.model) == wx.NOT_FOUND:
            self._model_choice.Append(options.model)
        self._model_choice.SetStringSelection(options.model)
        self._set_reasoning_choices_for_model(options.model, options.reasoning_effort)
        self._update_title()
        self._update_status_bar()
        self._session_controller.new_session(
            self._cwd,
            preferences=self._preferences,
            thread_options=self._thread_options,
        )

    def _start_default_session_and_send_prompt(self, text: str) -> None:
        """Start the default local session without blocking the UI, then send the prompt."""
        try:
            self._session_controller.new_session(
                self._cwd,
                preferences=self._preferences,
                thread_options=self._thread_options,
            )
            self._session_controller.send_prompt(text)
        except Exception as exc:
            wx.CallAfter(self._show_session_start_error, exc)
        finally:
            wx.CallAfter(self._clear_pending_prompt)

    def _show_session_start_error(self, exc: Exception) -> None:
        self.stop_working_status("Idle")
        wx.MessageBox(
            f"Could not start Codex session:\n\n{exc}",
            "Codex Session",
            wx.OK | wx.ICON_ERROR,
        )

    def _clear_pending_prompt(self) -> None:
        self._pending_prompt = False

    def _set_reasoning_choices_for_model(self, model: str, selected_effort: str) -> None:
        efforts = list(reasoning_efforts_for_model(model))
        selected = selected_effort if selected_effort in efforts else default_reasoning_effort_for_model(model)
        self._reasoning_choice.Set(efforts)
        self._reasoning_choice.SetStringSelection(selected)

    def _select_supported_reasoning_effort(self, model: str, effort: str) -> str:
        efforts = reasoning_efforts_for_model(model)
        if effort in efforts:
            return effort
        return default_reasoning_effort_for_model(model)

    # ------------------------------------------------------------------
    # Public API for SessionController
    # ------------------------------------------------------------------

    def append_transcript(self, text: str) -> None:
        """Append text to the transcript."""
        # Must use CallAfter since this may be called from background thread
        wx.CallAfter(self._transcript.AppendText, text)

    def set_turn_status(self, status: str) -> None:
        """Update the turn status in the status bar."""
        if status == "Idle" and self._working_started_at is not None:
            return
        self._turn_status = status
        wx.CallAfter(self._update_status_bar)

    def set_turn_details(self, details: str) -> None:
        """Update the visible non-transcript turn metadata."""
        self._turn_details = details
        wx.CallAfter(self._update_status_bar)

    def start_working_status(self) -> None:
        """Start desktop-style elapsed working status updates."""
        if self._working_started_at is None:
            self._working_started_at = time.monotonic()
            self._turn_status = format_working_status(0)
            wx.CallAfter(self._update_status_bar)
        wx.CallAfter(self._ensure_working_timer)

    def stop_working_status(self, status: str = "Idle") -> None:
        """Stop elapsed working status updates and set the final status."""
        self._working_started_at = None
        if self._working_timer.IsRunning():
            self._working_timer.Stop()
        self._working_gauge.SetValue(0)
        self.set_turn_status(status)

    def _ensure_working_timer(self) -> None:
        if not self._working_timer.IsRunning():
            self._working_timer.Start(1000)

    def _on_working_timer(self, event: wx.TimerEvent) -> None:
        if self._working_started_at is None:
            self._working_timer.Stop()
            return
        elapsed = int(time.monotonic() - self._working_started_at)
        self._turn_status = format_working_status(elapsed)
        self._working_gauge.Pulse()
        self._update_status_bar()

    def set_model(self, model: str) -> None:
        """Update the model name in the status bar and title."""
        self._model = model
        wx.CallAfter(self._update_title)
        wx.CallAfter(self._update_status_bar)

    def get_input_focus(self) -> None:
        """Set focus to the input field."""
        wx.CallAfter(self._input.SetFocus)


def _model_choices_with_current(current_model: str) -> list[str]:
    choices = load_model_choices()
    if current_model not in choices:
        choices.insert(0, current_model)
    return choices
