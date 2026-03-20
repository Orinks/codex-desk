"""
Tests for PiBridge.
Written FIRST (TDD) — implementation in wxpi/rpc_bridge.py must make these green.

fake_pi.py is used as a deterministic subprocess stand-in (no live Pi required).
"""
import sys
import os
import time
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wxpi.rpc_bridge import PiBridge

FAKE_PI = [sys.executable, os.path.join(os.path.dirname(__file__), "fake_pi.py")]


def test_happy_path(monkeypatch):
    """Bridge receives all expected event types from fake_pi on a simple prompt."""
    events = []
    bridge = PiBridge()
    monkeypatch.setattr("wxpi.rpc_bridge.PI_BINARY_ARGS", FAKE_PI)
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
    monkeypatch.setattr("wxpi.rpc_bridge.PI_BINARY_ARGS", FAKE_PI)
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
    monkeypatch.setattr("wxpi.rpc_bridge.PI_BINARY_ARGS", FAKE_PI)
    bridge.on_process_exit(lambda: exit_called.set())
    bridge.start(cwd="/tmp")
    bridge.send_prompt("hello")
    assert exit_called.wait(timeout=3.0), "on_process_exit callback was not called"


def test_multiple_event_callbacks(monkeypatch):
    """Multiple on_event callbacks all receive every event."""
    received_a = []
    received_b = []
    bridge = PiBridge()
    monkeypatch.setattr("wxpi.rpc_bridge.PI_BINARY_ARGS", FAKE_PI)
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
    monkeypatch.setattr("wxpi.rpc_bridge.PI_BINARY_ARGS", FAKE_PI)
    bridge.on_event(events.append)
    bridge.start(cwd="/tmp")
    # Do NOT send a prompt — fake_pi blocks waiting for one
    time.sleep(0.15)
    assert events == [], f"Expected no events before prompt, got: {events}"
