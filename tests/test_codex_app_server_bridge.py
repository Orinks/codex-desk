from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

from wxpi.codex_app_server_bridge import (
    CODEX_APP_SERVER_ARGS,
    CodexAppServerBridge,
    _classify_stderr_line,
    _summarize_file_changes,
)
from wxpi.preferences import AppPreferences, ThreadOptions


FAKE_CODEX = [sys.executable, str(Path(__file__).with_name("fake_codex_app_server.py"))]


def test_bridge_handshakes_starts_thread_and_runs_turn(monkeypatch, tmp_path):
    events = []
    exit_called = threading.Event()
    log_path = tmp_path / "client_messages.jsonl"
    monkeypatch.setenv("WXAGENT_FAKE_CODEX_LOG", str(log_path))
    monkeypatch.setattr("wxpi.codex_app_server_bridge.CODEX_APP_SERVER_ARGS", FAKE_CODEX)

    bridge = CodexAppServerBridge(client_name="wxagent-test", model="gpt-5.4")
    bridge.on_event(events.append)
    bridge.on_process_exit(exit_called.set)

    preferences = AppPreferences(personality="pragmatic")
    thread_options = ThreadOptions(
        model="gpt-5.5",
        reasoning_effort="high",
        sandbox="read-only",
        approval_policy="never",
        approvals_reviewer="auto_review",
    )

    bridge.start(cwd=str(tmp_path), preferences=preferences, thread_options=thread_options)
    bridge.send_prompt("hello")

    assert exit_called.wait(timeout=3.0), "fake Codex app-server never exited"
    assert [event["type"] for event in events] == [
        "agent_start",
        "turn_start",
        "message_update",
        "turn_end",
    ]
    assert events[2]["delta"] == "Hello from Codex"

    messages = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert [message["method"] for message in messages] == [
        "initialize",
        "initialized",
        "thread/start",
        "turn/start",
    ]
    assert messages[0]["params"]["clientInfo"]["name"] == "wxagent-test"
    assert messages[2]["params"] == {
        "cwd": str(tmp_path),
        "model": "gpt-5.5",
        "personality": "pragmatic",
        "sandbox": "read-only",
        "approvalPolicy": "never",
        "approvalsReviewer": "auto_review",
        "sessionStartSource": "startup",
    }
    assert messages[3]["params"]["threadId"] == "thr_test"
    assert messages[3]["params"]["input"] == [{"type": "text", "text": "hello"}]
    assert messages[3]["params"]["model"] == "gpt-5.5"
    assert messages[3]["params"]["effort"] == "high"
    assert messages[3]["params"]["approvalPolicy"] == "never"
    assert messages[3]["params"]["approvalsReviewer"] == "auto_review"


def test_send_prompt_requires_running_thread(tmp_path):
    bridge = CodexAppServerBridge()

    try:
        bridge.send_prompt("hello")
    except RuntimeError as exc:
        assert "start a Codex thread" in str(exc)
    else:
        raise AssertionError("send_prompt should fail before start()")


def test_codex_app_server_launch_disables_noisy_analytics():
    assert CODEX_APP_SERVER_ARGS[:2] == ["codex", "app-server"]
    assert "-c" in CODEX_APP_SERVER_ARGS
    assert "analytics.enabled=false" in CODEX_APP_SERVER_ARGS
    assert "suppress_unstable_features_warning=true" in CODEX_APP_SERVER_ARGS


def test_codex_403_plugin_and_analytics_warnings_are_debug_diagnostics():
    plugin_warning = (
        "WARN codex_core::plugins::startup_sync: remote plugin sync request to "
        "https://chatgpt.com/backend-api/plugins/list failed with 403 Forbidden"
    )
    analytics_warning = (
        "WARN codex_analytics::client: request to "
        "https://chatgpt.com/backend-api/codex/analytics-events/events failed: 403 Forbidden"
    )

    assert _classify_stderr_line(plugin_warning) == {
        "type": "diagnostic",
        "severity": "debug",
        "message": "Ignored non-fatal Codex app-server diagnostic.",
    }
    assert _classify_stderr_line(analytics_warning)["severity"] == "debug"


def test_structured_plugin_and_shell_snapshot_noise_are_debug_diagnostics():
    prompt_warning = (
        '{"timestamp":"2026-05-05T23:19:44Z","level":"WARN","fields":'
        '{"message":"ignoring facade.defaultPrompt: prompt must be at most 128 characters",'
        '"path":"C:\\\\Users\\\\joshu\\\\.codex\\\\.tmp\\\\plugins\\\\plugins\\\\build-ios-apps\\\\.codex\\\\plugin.json"},'
        '"target":"codex_core::plugins::manifest"}'
    )
    shell_warning = (
        '{"timestamp":"2026-05-05T23:19:45Z","level":"WARN","fields":'
        '{"message":"Failed to create shell snapshot for powershell: Shell snapshot not supported yet for PowerShell"},'
        '"target":"codex_core::shell_snapshot"}'
    )
    auth_warning = (
        '{"timestamp":"2026-05-05T23:19:45Z","level":"ERROR","fields":'
        '{"message":"worker quit fatal: Transport channel closed, when AuthRequired"},'
        '"target":"codex_core::plugins::manager"}'
    )

    assert _classify_stderr_line(prompt_warning)["severity"] == "debug"
    assert _classify_stderr_line(shell_warning)["severity"] == "debug"
    assert _classify_stderr_line(auth_warning)["severity"] == "debug"


def test_unexpected_stderr_stays_visible():
    assert _classify_stderr_line("error: app-server failed to start") == {
        "type": "diagnostic",
        "severity": "warning",
        "message": "error: app-server failed to start",
    }


def test_summarize_file_changes_from_codex_item():
    assert _summarize_file_changes(
        {
            "changes": [
                {"kind": "create"},
                {"kind": "edit"},
                {"kind": "modify"},
                {"kind": "delete"},
            ]
        }
    ) == {"created": 1, "edited": 2, "deleted": 1}
