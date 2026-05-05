from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

from wxpi.codex_app_server_bridge import CodexAppServerBridge


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

    bridge.start(cwd=str(tmp_path))
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
    assert messages[2]["params"]["model"] == "gpt-5.4"
    assert messages[3]["params"]["threadId"] == "thr_test"
    assert messages[3]["params"]["input"] == [{"type": "text", "text": "hello"}]


def test_send_prompt_requires_running_thread(tmp_path):
    bridge = CodexAppServerBridge()

    try:
        bridge.send_prompt("hello")
    except RuntimeError as exc:
        assert "start a Codex thread" in str(exc)
    else:
        raise AssertionError("send_prompt should fail before start()")
