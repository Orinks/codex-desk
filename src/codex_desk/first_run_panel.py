"""First-run panel shown when Codex is not found."""
import shutil
import subprocess
import sys
import threading

import wx

from codex_desk.constants import APP_NAME, CODEX_BINARY

# Use shell=True on Windows since npm is a .cmd batch file.
USE_SHELL = sys.platform == "win32"


class FirstRunPanel(wx.Panel):
    """Panel shown when Codex is not found."""

    CODEX_DOCS_URL = "https://developers.openai.com/codex/cli"

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, wx.ID_ANY)
        self._create_ui()

    def _create_ui(self) -> None:
        """Create the UI elements."""
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddStretchSpacer(1)

        # Title
        title = wx.StaticText(
            self,
            wx.ID_ANY,
            f"{APP_NAME} - Codex Not Found",
            style=wx.ALIGN_CENTER,
        )
        title.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, flag=wx.ALIGN_CENTER | wx.BOTTOM, border=20)

        # Message
        self._message_label = wx.StaticText(
            self,
            wx.ID_ANY,
            f"'{CODEX_BINARY}' was not found on your system.\n\n"
            "Install Codex, then sign in with your ChatGPT account or API key.\n",
            style=wx.ALIGN_CENTER,
        )
        sizer.Add(self._message_label, flag=wx.ALIGN_CENTER | wx.BOTTOM, border=10)

        # Progress text
        self._progress_label = wx.StaticText(
            self,
            wx.ID_ANY,
            "",
            style=wx.ALIGN_CENTER,
        )
        self._progress_label.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(self._progress_label, flag=wx.ALIGN_CENTER | wx.BOTTOM, border=10)

        # Buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self._install_btn = wx.Button(self, wx.ID_ANY, "Install Codex")
        self._install_btn.SetToolTip("Install Codex CLI with npm")
        self.Bind(wx.EVT_BUTTON, self._on_install, self._install_btn)
        button_sizer.Add(self._install_btn, flag=wx.RIGHT, border=10)

        # Manual setup button
        self._manual_btn = wx.Button(self, wx.ID_ANY, "Manual Setup")
        self._manual_btn.SetName("Open manual setup instructions")
        self.Bind(wx.EVT_BUTTON, self._on_manual, self._manual_btn)
        button_sizer.Add(self._manual_btn, flag=wx.RIGHT, border=10)

        # Retry button
        self._retry_btn = wx.Button(self, wx.ID_ANY, "Retry")
        self._retry_btn.SetToolTip("Retry connection to Codex")
        self.Bind(wx.EVT_BUTTON, self._on_retry, self._retry_btn)
        button_sizer.Add(self._retry_btn)

        sizer.Add(button_sizer, flag=wx.ALIGN_CENTER)

        sizer.AddStretchSpacer(1)

        # Set sizer
        self.SetSizer(sizer)

        # Set default button
        self._install_btn.SetDefault()

    def _set_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable all buttons."""
        self._install_btn.Enable(enabled)
        self._manual_btn.Enable(enabled)
        self._retry_btn.Enable(enabled)

    def _on_install(self, event: wx.CommandEvent) -> None:
        """Install Codex automatically."""
        # Check if npm is available
        if not shutil.which("npm"):
            wx.MessageBox(
                "Node.js/npm is required to install Codex.\n\n"
                "Please install Node.js from https://nodejs.org first.",
                "Node.js Required",
                wx.OK | wx.ICON_WARNING,
                self,
            )
            return

        # Start installation in background thread
        self._set_buttons_enabled(False)
        self._progress_label.SetLabel("Installing Codex...")
        self._install_btn.SetLabel("Installing...")

        thread = threading.Thread(target=self._install_codex)
        thread.daemon = True
        thread.start()

    def _install_codex(self) -> None:
        """Install Codex in background thread."""
        try:
            result = subprocess.run(
                ["npm", "install", "-g", "@openai/codex"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                shell=USE_SHELL,
            )

            if result.returncode != 0:
                wx.CallAfter(self._install_failed, result.stderr)
                return

            wx.CallAfter(self._progress_label.SetLabel, "Codex installed! Sign in to continue.")

            if shutil.which(CODEX_BINARY):
                wx.CallAfter(self._show_login_prompt)
            else:
                wx.CallAfter(
                    self._install_failed,
                    "Codex installation completed but 'codex' was not found on PATH.\n"
                    "Try restarting the app.",
                )

        except subprocess.TimeoutExpired:
            wx.CallAfter(self._install_failed, "Installation timed out. Please try again or use Manual Setup.")
        except Exception as e:
            wx.CallAfter(self._install_failed, f"Installation failed: {str(e)}")

    def _show_login_prompt(self) -> None:
        """Prompt user to sign in to Codex."""
        self._progress_label.SetLabel("Codex installed. Sign in from the Codex CLI if needed.")
        self._install_btn.SetLabel("Installed!")
        wx.MessageBox(
            "Codex is installed.\n\n"
            "If this is your first time using Codex, run 'codex' in a terminal and sign in.\n"
            "After sign-in, click Retry to continue.",
            "Codex Installed",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )
        self._set_buttons_enabled(True)
        self._install_btn.SetLabel("Reinstall Codex")

    def _install_succeeded(self) -> None:
        """Handle successful installation."""
        self._progress_label.SetLabel("Codex installed successfully!")
        self._install_btn.SetLabel("Installed!")

        # Check again after a short delay
        wx.CallAfter(self._retry, None)

    def _install_failed(self, message: str) -> None:
        """Handle installation failure."""
        self._progress_label.SetLabel("Installation failed")
        self._install_btn.SetLabel("Install Codex")
        self._set_buttons_enabled(True)

        wx.MessageBox(
            message,
            "Installation Failed",
            wx.OK | wx.ICON_ERROR,
            self,
        )

    def _on_manual(self, event: wx.CommandEvent) -> None:
        """Show manual setup instructions."""
        wx.LaunchDefaultBrowser(self.CODEX_DOCS_URL)

    def _on_retry(self, event: wx.CommandEvent) -> None:
        """Retry finding Codex on the system."""
        if not shutil.which(CODEX_BINARY):
            return
        event = wx.CommandEvent(wx.EVT_BUTTON.GetEventType(), self.GetId())
        event.SetEventObject(self)
        wx.PostEvent(self.GetParent(), event)


class FirstRunFrame(wx.Frame):
    """Standalone frame for first-run when Pi is not configured."""

    def __init__(self) -> None:
        super().__init__(
            None,
            wx.ID_ANY,
            f"{APP_NAME} — Setup",
            size=(500, 400),
        )

        self._panel = FirstRunPanel(self)
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.GetSizer().Add(self._panel, proportion=1, flag=wx.EXPAND)

        # Bind retry success event only to the retry button
        self.Bind(wx.EVT_BUTTON, self._on_retry_success, self._panel._retry_btn)

    def _on_retry_success(self, event: wx.CommandEvent) -> None:
        """Handle retry success - close this frame and show main window."""
        self.Close()
