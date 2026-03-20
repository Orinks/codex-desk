"""
PiBridge — manages a Pi subprocess over JSONL RPC.

PI_BINARY_ARGS is a module-level list so tests can monkeypatch it to point at
fake_pi.py without modifying any class state.
"""
import json
import subprocess
import sys
import threading
from typing import Callable, Optional

from wxpi.constants import PI_BINARY

# Monkeypatched in tests to point at tests/fake_pi.py
PI_BINARY_ARGS: list[str] = [PI_BINARY, "--mode", "rpc"]


class PiBridge:
    """Owns the Pi subprocess and a background reader thread.

    All callbacks are invoked from the reader thread. Callers that update
    wx widgets must wrap them in wx.CallAfter().
    """

    def __init__(self) -> None:
        self._proc: Optional["subprocess.Popen[bytes]"] = None
        self._thread: Optional[threading.Thread] = None
        self._callbacks: list[Callable[[dict], None]] = []
        self._exit_callbacks: list[Callable[[], None]] = []

    def start(self, cwd: str, session_path: Optional[str] = None,
              continue_session: bool = False) -> None:
        """Spawn Pi and start the background reader thread."""
        args = list(PI_BINARY_ARGS)
        if session_path:
            args += ["--session", session_path]
        if continue_session:
            args += ["--continue"]
        
        # On Windows, use shell=True to avoid the console window taking over.
        # This is the same approach used in first_run_panel.py for pi /login.
        use_shell = sys.platform == "win32"
        
        self._proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            shell=use_shell,
        )
        self._thread = threading.Thread(
            target=self._read_loop, daemon=True, name="pi-reader"
        )
        self._thread.start()

    def send_prompt(self, text: str) -> None:
        self._write({"type": "prompt", "content": text})

    def send_abort(self) -> None:
        self._write({"type": "abort"})

    def send_ui_response(self, request_id: str, result: object) -> None:
        self._write({"type": "confirm_response", "id": request_id, "result": result})

    def on_event(self, callback: Callable[[dict], None]) -> None:
        """Register a callback invoked for every incoming Pi event dict."""
        self._callbacks.append(callback)

    def on_process_exit(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked once when the Pi process exits."""
        self._exit_callbacks.append(callback)

    def stop(self) -> None:
        """Stop the Pi process and the reader thread."""
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None
        self._thread = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write(self, obj: dict) -> None:
        if self._proc and self._proc.stdin:
            line = json.dumps(obj).encode("utf-8") + b"\n"
            self._proc.stdin.write(line)
            self._proc.stdin.flush()

    def _read_loop(self) -> None:
        """Background thread: read JSONL from Pi stdout, dispatch to callbacks.

        Splits on raw 0x0A bytes only — U+2028/U+2029 inside JSON strings are
        safe because they are encoded as their escaped forms in JSON output.
        """
        assert self._proc and self._proc.stdout
        while True:
            raw = self._proc.stdout.readline()  # byte-level; splits only on 0x0A
            if not raw:
                break
            try:
                event = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            for cb in self._callbacks:
                cb(event)
        for cb in self._exit_callbacks:
            cb()
