"""Codex app-server bridge for wxAgent.

This module owns the local ``codex app-server`` subprocess and speaks the
JSON-RPC-over-JSONL protocol documented by OpenAI. It normalizes the small set
of app-server messages the current wx UI needs into the existing internal event
shape so the UI can evolve without depending on every Codex protocol detail.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from typing import Callable

from wxpi.constants import CODEX_BINARY
from wxpi.preferences import AppPreferences, ThreadOptions

CODEX_APP_SERVER_ARGS: list[str] = [
    CODEX_BINARY,
    "app-server",
    "-c",
    "analytics.enabled=false",
    "-c",
    "suppress_unstable_features_warning=true",
]
USE_SHELL = sys.platform == "win32"

BENIGN_CODEX_WARNING_HINTS = (
    "codex_core::plugins::startup_sync",
    "codex_core::plugins::manager",
    "codex_analytics::client",
    "backend-api/plugins/list",
    "backend-api/plugins/featured",
    "backend-api/codex/analytics-events/events",
)


class CodexAppServerBridge:
    """Manage a local Codex app-server process over JSONL."""

    def __init__(self, client_name: str = "wxagent", model: str = "gpt-5.4") -> None:
        self._client_name = client_name
        self._model = model
        self._proc: subprocess.Popen[str] | None = None
        self._thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
        self._callbacks: list[Callable[[dict], None]] = []
        self._exit_callbacks: list[Callable[[], None]] = []
        self._next_id = 0
        self._thread_start_request_id: int | None = None
        self._thread_id: str | None = None
        self._thread_ready = threading.Event()
        self._preferences = AppPreferences()
        self._thread_options = ThreadOptions(model=model)

    def start(
        self,
        cwd: str,
        session_path: str | None = None,
        continue_session: bool = False,
        preferences: AppPreferences | None = None,
        thread_options: ThreadOptions | None = None,
    ) -> None:
        """Start Codex app-server and open a thread for the selected workspace."""
        if session_path or continue_session:
            raise NotImplementedError("Codex thread resume is not wired into wxAgent yet")
        self._preferences = preferences or AppPreferences()
        self._thread_options = thread_options or ThreadOptions(model=self._model)
        self._model = self._thread_options.model

        self._proc = subprocess.Popen(
            list(CODEX_APP_SERVER_ARGS),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            shell=USE_SHELL,
            text=True,
            encoding="utf-8",
        )
        self._thread = threading.Thread(
            target=self._read_loop,
            daemon=True,
            name="codex-app-server-reader",
        )
        self._thread.start()
        self._stderr_thread = threading.Thread(
            target=self._read_stderr_loop,
            daemon=True,
            name="codex-app-server-stderr-reader",
        )
        self._stderr_thread.start()

        self._send_request(
            "initialize",
            {
                "clientInfo": {
                    "name": self._client_name,
                    "title": "wxAgent",
                    "version": "0.1.0",
                }
            },
        )
        self._send_notification("initialized", {})
        self._thread_start_request_id = self._send_request(
            "thread/start",
            {
                "cwd": cwd,
                "model": self._thread_options.model,
                "personality": self._preferences.personality,
                "sandbox": self._thread_options.sandbox,
                "approvalPolicy": self._thread_options.approval_policy,
                "approvalsReviewer": self._thread_options.approvals_reviewer,
                "sessionStartSource": "startup",
            },
        )

        if not self._thread_ready.wait(timeout=5.0):
            self.stop()
            raise RuntimeError("Codex app-server did not start a thread")

    def send_prompt(self, text: str) -> None:
        """Start a Codex turn from user text."""
        if not self._thread_id:
            raise RuntimeError("start a Codex thread before sending prompts")
        self._send_request(
            "turn/start",
            {
                "threadId": self._thread_id,
                "input": [{"type": "text", "text": text}],
                "model": self._thread_options.model,
                "effort": self._thread_options.reasoning_effort,
                "approvalPolicy": self._thread_options.approval_policy,
                "approvalsReviewer": self._thread_options.approvals_reviewer,
            },
        )

    def set_thread_options(self, thread_options: ThreadOptions) -> None:
        """Update options used for subsequent turns."""
        self._thread_options = thread_options

    def send_abort(self) -> None:
        """Request cancellation of the active turn when supported by Codex."""
        if self._thread_id:
            self._send_request("turn/abort", {"threadId": self._thread_id})

    def send_ui_response(self, request_id: str, result: object) -> None:
        """Send an approval response back to Codex."""
        self._send_request("approval/answer", {"id": request_id, "result": result})

    def on_event(self, callback: Callable[[dict], None]) -> None:
        self._callbacks.append(callback)

    def on_process_exit(self, callback: Callable[[], None]) -> None:
        self._exit_callbacks.append(callback)

    def stop(self) -> None:
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None
        self._thread = None
        self._stderr_thread = None

    def _send_request(self, method: str, params: dict) -> int:
        request_id = self._next_id
        self._next_id += 1
        self._write({"method": method, "id": request_id, "params": params})
        return request_id

    def _send_notification(self, method: str, params: dict) -> None:
        self._write({"method": method, "params": params})

    def _write(self, obj: dict) -> None:
        if not self._proc or not self._proc.stdin:
            raise RuntimeError("Codex app-server is not running")
        self._proc.stdin.write(json.dumps(obj) + "\n")
        self._proc.stdin.flush()

    def _read_loop(self) -> None:
        assert self._proc and self._proc.stdout
        while True:
            line = self._proc.stdout.readline()
            if not line:
                break
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            self._handle_message(message)
        for callback in self._exit_callbacks:
            callback()

    def _read_stderr_loop(self) -> None:
        assert self._proc and self._proc.stderr
        while True:
            line = self._proc.stderr.readline()
            if not line:
                break
            diagnostic = _classify_stderr_line(line)
            if diagnostic:
                self._dispatch(diagnostic)

    def _handle_message(self, message: dict) -> None:
        if message.get("id") == self._thread_start_request_id and "result" in message:
            thread = message["result"].get("thread", {})
            self._thread_id = thread.get("id")
            self._thread_ready.set()
            self._dispatch({"type": "agent_start", "model": self._model, "session_id": self._thread_id or ""})
            return

        method = message.get("method")
        params = message.get("params", {})
        if method == "turn/started":
            turn_id = params.get("turn", {}).get("id", "")
            self._dispatch({"type": "turn_start", "turn_id": turn_id})
        elif method == "turn/completed":
            turn_id = params.get("turn", {}).get("id", "")
            self._dispatch({"type": "turn_end", "turn_id": turn_id})
        elif method == "item/completed":
            item = params.get("item", {})
            text = _extract_item_text(item)
            if item.get("type") in {"agent_message", "agentMessage"} and text:
                self._dispatch({"type": "message_update", "delta": text})
            reasoning = _extract_reasoning_text(item)
            if reasoning:
                self._dispatch({"type": "reasoning_update", "delta": reasoning})
            file_summary = _summarize_file_changes(item)
            if any(file_summary.values()):
                self._dispatch({"type": "file_change_summary", **file_summary})

    def _dispatch(self, event: dict) -> None:
        for callback in self._callbacks:
            callback(event)


def _extract_item_text(item: dict) -> str:
    text = item.get("text") or item.get("message")
    if text:
        return str(text)

    content = item.get("content")
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(str(part.get("text", "")))
        return "".join(parts)

    return ""


def _extract_reasoning_text(item: dict) -> str:
    if item.get("type") not in {"reasoning", "reasoningSummary", "reasoning_summary"}:
        return ""
    return _extract_item_text(item)


def _summarize_file_changes(item: dict) -> dict[str, int]:
    created = _coerce_count(item, "created")
    edited = _coerce_count(item, "edited")
    deleted = _coerce_count(item, "deleted")

    changes = item.get("changes")
    if isinstance(changes, list):
        for change in changes:
            if not isinstance(change, dict):
                continue
            kind = str(change.get("kind") or change.get("type") or change.get("action") or "").lower()
            if kind in {"create", "created", "add", "added", "new"}:
                created += 1
            elif kind in {"edit", "edited", "modify", "modified", "update", "updated", "write"}:
                edited += 1
            elif kind in {"delete", "deleted", "remove", "removed"}:
                deleted += 1

    return {"created": created, "edited": edited, "deleted": deleted}


def _coerce_count(item: dict, key: str) -> int:
    value = item.get(key, 0)
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(value, 0)
    return 0


def _classify_stderr_line(line: str) -> dict | None:
    message = line.strip()
    if not message:
        return None

    if any(hint in message for hint in BENIGN_CODEX_WARNING_HINTS) and "403" in message:
        return {
            "type": "diagnostic",
            "severity": "debug",
            "message": "Ignored non-fatal Codex plugin/analytics 403 warning.",
        }

    return {"type": "diagnostic", "severity": "warning", "message": message}
