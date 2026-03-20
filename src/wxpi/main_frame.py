"""Main window frame for wxPi."""
import os
import wx

from wxpi.constants import APP_NAME
from wxpi.provider_panel import ProviderDialog
from wxpi.session_controller import SessionController


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
        quit_item = wx.MenuItem(file_menu, wx.ID_EXIT, f"Quit\tCtrl+Q")
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
        
        # Provider management
        providers_item = wx.MenuItem(edit_menu, wx.ID_ANY, "Manage Providers...\tCtrl+P")
        edit_menu.Append(providers_item)
        self.Bind(wx.EVT_MENU, self._on_manage_providers, providers_item)

        # Help menu
        help_menu = wx.Menu()
        about_item = wx.MenuItem(help_menu, wx.ID_ABOUT, "About")
        help_menu.Append(about_item)
        self.Bind(wx.EVT_MENU, self._on_about, about_item)

        menubar.Append(file_menu, "File")
        menubar.Append(edit_menu, "Edit")
        menubar.Append(help_menu, "Help")

        self.SetMenuBar(menubar)

    def _create_panels(self) -> None:
        """Create the main panel layout."""
        # Main panel holds transcript and input
        main_panel = wx.Panel(self, wx.ID_ANY)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Transcript area (read-only TextCtrl per ARCH recommendation)
        self._transcript = wx.TextCtrl(
            main_panel,
            wx.ID_ANY,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
        )
        self._transcript.SetName("Transcript")
        # Set monospace font for transcript
        font = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName="Courier New")
        self._transcript.SetFont(font)

        # Input area (multiline text control)
        self._input = wx.TextCtrl(
            main_panel,
            wx.ID_ANY,
            style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER,
        )
        self._input.SetName("Message input")
        # Set initial hint text
        self._input.SetHint("Enter your prompt... (Enter to send, Shift+Enter for new line)")

        # Bind input events
        self.Bind(wx.EVT_TEXT_ENTER, self._on_submit_prompt, self._input)

        sizer.Add(self._transcript, proportion=8, flag=wx.EXPAND)
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

    def _on_new_session(self, event: wx.CommandEvent) -> None:
        """Start a new session."""
        dlg = wx.DirDialog(
            self,
            "Choose a working directory for the new session:",
            defaultPath=self._cwd,
        )
        if dlg.ShowModal() == wx.ID_OK:
            self._cwd = dlg.GetPath()
            self._update_title()
            self._update_status_bar()
            self._session_controller.new_session(self._cwd)

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
        dlg = wx.DirDialog(
            self,
            "Choose a working directory:",
            defaultPath=self._cwd,
        )
        if dlg.ShowModal() == wx.ID_OK:
            self._cwd = dlg.GetPath()
            self._update_title()
            self._update_status_bar()
            # Start a new session in the new directory
            self._session_controller.new_session(self._cwd)

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

    def _on_manage_providers(self, event: wx.CommandEvent) -> None:
        """Open provider management dialog."""
        dlg = ProviderDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

    def _on_about(self, event: wx.CommandEvent) -> None:
        """Show about dialog."""
        wx.MessageBox(
            f"{APP_NAME}\n\n"
            "A native accessible wxPython frontend for the Pi coding agent.\n\n"
            "Built with wxPython.",
            f"About {APP_NAME}",
            wx.OK | wx.ICON_INFORMATION,
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