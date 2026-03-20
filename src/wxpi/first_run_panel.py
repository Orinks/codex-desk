"""First-run panel shown when Pi is not found or not configured."""
import shutil
import subprocess
import sys
import threading

import wx

# Use shell=True on Windows since npm/pi are .cmd batch files
USE_SHELL = sys.platform == "win32"

from wxpi.constants import APP_NAME, PI_BINARY


def check_has_provider() -> bool:
    """Check if Pi has a provider configured.
    
    Returns True if Pi has at least one provider configured (OAuth or API key),
    False otherwise.
    """
    import json
    import os
    
    # Check OAuth tokens in auth.json
    auth_path = os.path.expanduser("~/.pi/agent/auth.json")
    if os.path.exists(auth_path):
        try:
            with open(auth_path, 'r') as f:
                auth_data = json.load(f)
                if auth_data.get("tokens"):
                    return True
        except (json.JSONDecodeError, IOError):
            pass
    
    # Also check for API keys in .env file
    env_file = os.path.expanduser("~/.pi/agent/.env")
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    if line.strip() and '=' in line:
                        return True
        except (IOError):
            pass
    
    return False


class FirstRunPanel(wx.Panel):
    """Panel shown when Pi is not found or not configured."""

    PI_INSTALL_URL = "https://github.com/badlogic/pi-mono"
    PI_DOCS_URL = "https://github.com/badlogic/pi-mono#installation"

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, wx.ID_ANY)

        # Check if Pi is installed but no provider configured
        self._pi_installed = shutil.which(PI_BINARY) is not None
        self._provider_configured = check_has_provider()
        
        # Always create UI - but show appropriate message based on state
        self._create_ui()
        
        # Update message based on state
        if self._pi_installed and not self._provider_configured:
            # Pi is installed but no provider - show different message and button
            self._message_label.SetLabel(
                f"Pi is installed but no provider configured.\n\n"
                "Choose an AI provider to get started.\n"
            )
            self._install_btn.SetLabel("Configure Provider")
            self._install_btn.SetName("Configure AI provider")
            # Unbind install handler from install button specifically and bind provider config
            self.Unbind(wx.EVT_BUTTON, handler=self._on_install, source=self._install_btn)
            self.Bind(wx.EVT_BUTTON, self._on_configure_provider, self._install_btn)
            self._install_btn.SetDefault()

    def _create_ui(self) -> None:
        """Create the UI elements."""
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddStretchSpacer(1)

        # Title
        title = wx.StaticText(
            self,
            wx.ID_ANY,
            f"{APP_NAME} — Pi Not Configured",
            style=wx.ALIGN_CENTER,
        )
        title.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, flag=wx.ALIGN_CENTER | wx.BOTTOM, border=20)

        # Message
        self._message_label = wx.StaticText(
            self,
            wx.ID_ANY,
            f"'{PI_BINARY}' was not found on your system.\n\n"
            "Click 'Install Pi' to automatically install it, or configure manually.\n",
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

        # Install Pi button
        self._install_btn = wx.Button(self, wx.ID_ANY, "Install Pi")
        self._install_btn.SetName("Install Pi automatically")
        self.Bind(wx.EVT_BUTTON, self._on_install, self._install_btn)
        button_sizer.Add(self._install_btn, flag=wx.RIGHT, border=10)

        # Manual setup button
        self._manual_btn = wx.Button(self, wx.ID_ANY, "Manual Setup")
        self._manual_btn.SetName("Open manual setup instructions")
        self.Bind(wx.EVT_BUTTON, self._on_manual, self._manual_btn)
        button_sizer.Add(self._manual_btn, flag=wx.RIGHT, border=10)

        # Retry button
        self._retry_btn = wx.Button(self, wx.ID_ANY, "Retry")
        self._retry_btn.SetName("Retry connection to Pi")
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
        """Install Pi automatically."""
        # Check if npm is available
        if not shutil.which("npm"):
            wx.MessageBox(
                "Node.js/npm is required to install Pi.\n\n"
                "Please install Node.js from https://nodejs.org first.",
                "Node.js Required",
                wx.OK | wx.ICON_WARNING,
                self,
            )
            return

        # Start installation in background thread
        self._set_buttons_enabled(False)
        self._progress_label.SetLabel("Installing Pi...")
        self._install_btn.SetLabel("Installing...")

        thread = threading.Thread(target=self._install_pi)
        thread.daemon = True
        thread.start()

    def _install_pi(self) -> None:
        """Install Pi in background thread."""
        try:
            # Run npm install -g @mariozechner/pi-coding-agent
            result = subprocess.run(
                ["npm", "install", "-g", "@mariozechner/pi-coding-agent"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                shell=USE_SHELL,
            )

            if result.returncode != 0:
                wx.CallAfter(self._install_failed, result.stderr)
                return

            wx.CallAfter(self._progress_label.SetLabel, "Pi installed! Running setup...")

            # Check if Pi is now available
            if shutil.which(PI_BINARY):
                # Prompt user to run pi /login manually (it opens browser for OAuth)
                wx.CallAfter(self._show_login_prompt)
            else:
                wx.CallAfter(self._install_failed, "Pi installation completed but 'pi' not found on PATH.\nTry restarting the app.")

        except subprocess.TimeoutExpired:
            wx.CallAfter(self._install_failed, "Installation timed out. Please try again or use Manual Setup.")
        except Exception as e:
            wx.CallAfter(self._install_failed, f"Installation failed: {str(e)}")

    def _show_login_prompt(self) -> None:
        """Prompt user to configure a provider for Pi."""
        self._progress_label.SetLabel("✓ Pi installed! Configuring provider...")
        self._install_btn.SetLabel("Installed!")
        
        # Show the provider configuration dialog so user can choose which
        # provider to configure (OAuth, API key, AWS, or local Ollama)
        from wxpi.provider_panel import ProviderDialog
        dlg = ProviderDialog(self)
        dlg.ShowModal()
        dlg.Destroy()
        
        # Check if a provider was actually configured
        # Check both OAuth tokens in auth.json AND API keys in .env
        import json
        import os
        has_provider = False
        
        # Check OAuth tokens in auth.json
        auth_path = os.path.expanduser("~/.pi/agent/auth.json")
        if os.path.exists(auth_path):
            try:
                with open(auth_path, 'r') as f:
                    auth_data = json.load(f)
                    if auth_data.get("tokens"):
                        has_provider = True
            except (json.JSONDecodeError, IOError):
                pass
        
        # Also check for API keys in .env file
        if not has_provider:
            env_file = os.path.expanduser("~/.pi/agent/.env")
            if os.path.exists(env_file):
                try:
                    with open(env_file, 'r') as f:
                        for line in f:
                            if line.strip() and '=' in line:
                                # Has any API key setting
                                has_provider = True
                                break
                except (IOError):
                    pass
        
        if has_provider:
            # Provider configured - show success message
            wx.MessageBox(
                "Provider configured successfully!\n\n"
                "Click 'Retry' to continue to the main window.\n"
                "You can also manage providers later from the Edit menu.",
                "Setup Complete",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
        else:
            # No provider configured - show message with options
            wx.MessageBox(
                "Pi has been installed.\n\n"
                "No provider was configured. You can:\n"
                "- Click 'Configure Provider' in the dialog to add one\n"
                "- Use 'pi /login' in a terminal for OAuth login\n"
                "- Set API keys via environment variables\n\n"
                "Click 'Retry' once you've configured a provider.",
                "Provider Not Configured",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
        
        # Re-enable all buttons so user can retry or go manual
        self._set_buttons_enabled(True)
        self._install_btn.SetLabel("Reinstall Pi")

    def _install_succeeded(self) -> None:
        """Handle successful installation."""
        self._progress_label.SetLabel("✓ Pi installed successfully!")
        self._install_btn.SetLabel("Installed!")

        # Check again after a short delay
        wx.CallAfter(self._retry, None)

    def _install_failed(self, message: str) -> None:
        """Handle installation failure."""
        self._progress_label.SetLabel("✗ Installation failed")
        self._install_btn.SetLabel("Install Pi")
        self._set_buttons_enabled(True)

        wx.MessageBox(
            message,
            "Installation Failed",
            wx.OK | wx.ICON_ERROR,
            self,
        )

    def _on_manual(self, event: wx.CommandEvent) -> None:
        """Show manual setup instructions."""
        wx.LaunchDefaultBrowser(self.PI_DOCS_URL)

    def _on_configure_provider(self, event: wx.CommandEvent) -> None:
        """Configure provider when Pi is installed but no provider configured."""
        # Show the provider configuration dialog so user can choose which
        # provider to configure (OAuth, API key, AWS, or local Ollama)
        from wxpi.provider_panel import ProviderDialog
        dlg = ProviderDialog(self)
        dlg.ShowModal()
        dlg.Destroy()
        
        # Check if a provider was actually configured
        if check_has_provider():
            # Provider configured - close the frame to let app continue
            event = wx.CommandEvent(wx.EVT_BUTTON.GetEventType(), self.GetId())
            event.SetEventObject(self)
            wx.PostEvent(self.GetParent(), event)
        else:
            # No provider configured - show message with options
            wx.MessageBox(
                "No provider was configured.\n\n"
                "You can:\n"
                "- Click 'Configure Provider' in the dialog to add one\n"
                "- Use 'pi /login' in a terminal for OAuth login\n"
                "- Set API keys via environment variables\n\n"
                "Click 'Retry' once you've configured a provider.",
                "Provider Not Configured",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )

    def _on_retry(self, event: wx.CommandEvent) -> None:
        """Retry finding Pi on the system."""
        # Check both that Pi exists AND that it has a provider configured
        if not shutil.which(PI_BINARY):
            return
        
        # Check if Pi has a provider configured (including .env for API keys)
        if check_has_provider():
            # Pi has a provider - close the frame to let app continue
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