"""
Tests for PiBridge.
Written FIRST (TDD) — implementation in codex_desk/rpc_bridge.py must make these green.

fake_pi.py and its variants are deterministic subprocess stand-ins (no live Pi required).
"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codex_desk.rpc_bridge import PiBridge

FAKE_PI = [sys.executable, os.path.join(os.path.dirname(__file__), "fake_pi.py")]
FAKE_PI_ABORT = [sys.executable, os.path.join(os.path.dirname(__file__), "fake_pi_abort.py")]
FAKE_PI_CONFIRM = [sys.executable, os.path.join(os.path.dirname(__file__), "fake_pi_confirm.py")]
FAKE_PI_UNICODE = [sys.executable, os.path.join(os.path.dirname(__file__), "fake_pi_unicode.py")]


def test_happy_path(monkeypatch):
    """Bridge receives all expected event types from fake_pi on a simple prompt."""
    events = []
    bridge = PiBridge()
    monkeypatch.setattr("codex_desk.rpc_bridge.PI_BINARY_ARGS", FAKE_PI)
    bridge.on_event(events.append)
    bridge.start(cwd="/tmp")
    bridge.send_prompt("hello")
    time.sleep(0.5)

    types = [e["type"] for e in events]
    assert "agent_start" in types
    assert "message_update" in types
    assert "agent_end" in types


def test_message_update_deltas(monkeypatch):
    """All delta values from fake_pi are received in order."""
    events = []
    bridge = PiBridge()
    monkeypatch.setattr("codex_desk.rpc_bridge.PI_BINARY_ARGS", FAKE_PI)
    bridge.on_event(events.append)
    bridge.start(cwd="/tmp")
    bridge.send_prompt("hello")
    time.sleep(0.5)

    deltas = [e["delta"] for e in events if e["type"] == "message_update"]
    assert deltas == ["Hello ", "world"]


def test_exit_callback_fires(monkeypatch):
    """on_process_exit callback is called after fake_pi terminates."""
    exit_called = threading.Event()
    bridge = PiBridge()
    monkeypatch.setattr("codex_desk.rpc_bridge.PI_BINARY_ARGS", FAKE_PI)
    bridge.on_process_exit(lambda: exit_called.set())
    bridge.start(cwd="/tmp")
    bridge.send_prompt("hello")
    assert exit_called.wait(timeout=3.0), "on_process_exit callback was not called"


def test_multiple_event_callbacks(monkeypatch):
    """Multiple on_event callbacks all receive every event."""
    received_a = []
    received_b = []
    bridge = PiBridge()
    monkeypatch.setattr("codex_desk.rpc_bridge.PI_BINARY_ARGS", FAKE_PI)
    bridge.on_event(received_a.append)
    bridge.on_event(received_b.append)
    bridge.start(cwd="/tmp")
    bridge.send_prompt("hi")
    time.sleep(0.5)

    assert len(received_a) == len(received_b)
    assert len(received_a) > 0


def test_no_events_before_prompt(monkeypatch):
    """Bridge starts but emits nothing until a prompt is sent."""
    events = []
    bridge = PiBridge()
    monkeypatch.setattr("codex_desk.rpc_bridge.PI_BINARY_ARGS", FAKE_PI)
    bridge.on_event(events.append)
    bridge.start(cwd="/tmp")
    time.sleep(0.15)
    assert events == [], f"Expected no events before prompt, got: {events}"


def test_send_abort_round_trip(monkeypatch):
    """send_abort writes an abort message that the backend can react to."""
    events = []
    exit_called = threading.Event()
    bridge = PiBridge()
    monkeypatch.setattr("codex_desk.rpc_bridge.PI_BINARY_ARGS", FAKE_PI_ABORT)
    bridge.on_event(events.append)
    bridge.on_process_exit(lambda: exit_called.set())
    bridge.start(cwd="/tmp")
    bridge.send_prompt("hello")
    time.sleep(0.1)
    bridge.send_abort()

    assert exit_called.wait(timeout=3.0), "abort path never exited"
    assert events[-1] == {"type": "agent_end", "status": "aborted"}


def test_confirm_round_trip(monkeypatch):
    """Bridge can send a confirm_response back to the backend."""
    events = []
    exit_called = threading.Event()
    bridge = PiBridge()
    monkeypatch.setattr("codex_desk.rpc_bridge.PI_BINARY_ARGS", FAKE_PI_CONFIRM)
    bridge.on_event(events.append)
    bridge.on_process_exit(lambda: exit_called.set())
    bridge.start(cwd="/tmp")
    bridge.send_prompt("hello")

    deadline = time.time() + 2.0
    while time.time() < deadline:
        confirm_events = [e for e in events if e.get("type") == "confirm"]
        if confirm_events:
            break
        time.sleep(0.02)
    else:
        raise AssertionError("confirm event never arrived")

    bridge.send_ui_response("req-1", True)
    assert exit_called.wait(timeout=3.0), "confirm path never exited"
    deltas = [e["delta"] for e in events if e.get("type") == "message_update"]
    assert deltas == ["confirmed:True"]


def test_unicode_separators_survive_jsonl_round_trip(monkeypatch):
    """U+2028/U+2029 inside JSON strings must survive the bridge unchanged."""
    events = []
    exit_called = threading.Event()
    bridge = PiBridge()
    monkeypatch.setattr("codex_desk.rpc_bridge.PI_BINARY_ARGS", FAKE_PI_UNICODE)
    bridge.on_event(events.append)
    bridge.on_process_exit(lambda: exit_called.set())
    bridge.start(cwd="/tmp")
    bridge.send_prompt("hello")
    assert exit_called.wait(timeout=3.0), "unicode fixture never exited"

    deltas = [e["delta"] for e in events if e.get("type") == "message_update"]
    assert deltas == ["line1\u2028line2\u2029line3"]
