"""wxPi application entry point."""
import shutil
import sys

import wx

from wxpi.constants import APP_NAME, PI_BINARY
from wxpi.first_run_panel import FirstRunFrame
from wxpi.main_frame import MainFrame
from wxpi.auth_service import AuthService


def check_pi_configured() -> bool:
    """Check if Pi has usable auth configured."""
    return AuthService().is_configured()


class WxPiApp(wx.App):
    """wxPi application class."""

    def OnInit(self) -> bool:
        """Initialize the application."""
        self.SetAppName(APP_NAME)
        self.SetVendorName("wxPi")

        # Check if Pi is available on PATH and has a provider configured
        if not shutil.which(PI_BINARY):
            # Pi not installed - show first-run panel
            self._show_first_run()
        elif not check_pi_configured():
            # Pi installed but no provider configured - show first-run panel
            self._show_first_run()
        else:
            # Show main window
            self._show_main()

        return True

    def _show_first_run(self) -> None:
        """Show the first-run panel when Pi is not found."""
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
        # Check if Pi is now available
        if shutil.which(PI_BINARY):
            self._first_run_frame.Close()
            self._show_main()


def main() -> int:
    """Application entry point."""
    app = WxPiApp(False)
    return app.MainLoop()


if __name__ == "__main__":
    sys.exit(main())
