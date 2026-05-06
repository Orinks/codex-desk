"""Codex Desk application entry point."""
import shutil
import sys

import wx

from codex_desk.constants import APP_NAME, CODEX_BINARY
from codex_desk.first_run_panel import FirstRunFrame
from codex_desk.main_frame import MainFrame


def check_codex_available() -> bool:
    """Return True when the Codex CLI is available on PATH."""
    return shutil.which(CODEX_BINARY) is not None


class CodexDeskApp(wx.App):
    """Codex Desk application class."""

    def OnInit(self) -> bool:
        """Initialize the application."""
        self.SetAppName(APP_NAME)
        self.SetVendorName("Codex Desk")

        # Check if Codex is available on PATH.
        if not check_codex_available():
            self._show_first_run()
        else:
            self._show_main()

        return True

    def _show_first_run(self) -> None:
        """Show the first-run panel when Codex is not found."""
        self._first_run_frame = FirstRunFrame()
        self._first_run_frame.Bind(wx.EVT_BUTTON, self._on_retry_success)
        self._first_run_frame.Show()
        self.SetTopWindow(self._first_run_frame)

    def _show_main(self) -> None:
        """Show the main window."""
        self._main_frame = MainFrame()
        self._main_frame.Show()
        self.SetTopWindow(self._main_frame)

    def _on_retry_success(self, event: wx.CommandEvent) -> None:
        """Handle retry success - close first-run and show main window."""
        # Check if Codex is now available
        if check_codex_available():
            self._first_run_frame.Close()
            self._show_main()


def main() -> int:
    """Application entry point."""
    app = CodexDeskApp(False)
    return app.MainLoop()


if __name__ == "__main__":
    sys.exit(main())
