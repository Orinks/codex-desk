"""
Tests for rpc_events.parse_event().
Written FIRST (TDD) — implementation in wxpi/rpc_events.py must make these green.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from wxpi.rpc_events import (
    parse_event,
    AgentStartEvent,
    MessageUpdateEvent,
    TurnStartEvent,
    TurnEndEvent,
    ToolExecutionStartEvent,
    ToolExecutionEndEvent,
    ConfirmEvent,
    AgentEndEvent,
    FileChangeSummaryEvent,
    ReasoningUpdateEvent,
)


def test_parse_agent_start():
    raw = {"type": "agent_start", "model": "claude-3-5", "session_id": "abc123"}
    event = parse_event(raw)
    assert isinstance(event, AgentStartEvent)
    assert event.model == "claude-3-5"
    assert event.session_id == "abc123"


def test_parse_message_update():
    raw = {"type": "message_update", "delta": "Hello world"}
    event = parse_event(raw)
    assert isinstance(event, MessageUpdateEvent)
    assert event.delta == "Hello world"
    assert event.completed is False


def test_parse_completed_message_update():
    raw = {"type": "message_update", "delta": "Hello world", "completed": True}
    event = parse_event(raw)
    assert isinstance(event, MessageUpdateEvent)
    assert event.delta == "Hello world"
    assert event.completed is True


def test_parse_turn_start():
    raw = {"type": "turn_start", "turn_id": "t1"}
    event = parse_event(raw)
    assert isinstance(event, TurnStartEvent)
    assert event.turn_id == "t1"


def test_parse_turn_end():
    raw = {"type": "turn_end", "turn_id": "t1"}
    event = parse_event(raw)
    assert isinstance(event, TurnEndEvent)
    assert event.turn_id == "t1"


def test_parse_confirm():
    raw = {
        "type": "confirm",
        "id": "req1",
        "tool": "bash",
        "args": {"command": "ls /tmp"},
        "cwd": "/tmp",
    }
    event = parse_event(raw)
    assert isinstance(event, ConfirmEvent)
    assert event.tool == "bash"
    assert event.id == "req1"
    assert event.cwd == "/tmp"
    assert event.args == {"command": "ls /tmp"}


def test_parse_tool_execution_start():
    raw = {
        "type": "tool_execution_start",
        "tool": "read",
        "args": {"path": "/etc/hosts"},
        "request_id": "r42",
    }
    event = parse_event(raw)
    assert isinstance(event, ToolExecutionStartEvent)
    assert event.tool == "read"
    assert event.request_id == "r42"


def test_parse_tool_execution_end_success():
    raw = {"type": "tool_execution_end", "status": "success", "exit_code": 0}
    event = parse_event(raw)
    assert isinstance(event, ToolExecutionEndEvent)
    assert event.status == "success"
    assert event.exit_code == 0


def test_parse_tool_execution_end_no_exit_code():
    raw = {"type": "tool_execution_end", "status": "success"}
    event = parse_event(raw)
    assert isinstance(event, ToolExecutionEndEvent)
    assert event.exit_code is None


def test_parse_agent_end():
    raw = {"type": "agent_end"}
    event = parse_event(raw)
    assert isinstance(event, AgentEndEvent)


def test_parse_reasoning_update():
    raw = {"type": "reasoning_update", "delta": "Inspecting project files."}
    event = parse_event(raw)
    assert isinstance(event, ReasoningUpdateEvent)
    assert event.delta == "Inspecting project files."


def test_parse_file_change_summary():
    raw = {"type": "file_change_summary", "created": 1, "edited": 2, "deleted": 0}
    event = parse_event(raw)
    assert isinstance(event, FileChangeSummaryEvent)
    assert event.created == 1
    assert event.edited == 2
    assert event.deleted == 0


def test_parse_unknown_returns_dict():
    """Unknown event types must pass through unchanged (forward compatibility)."""
    raw = {"type": "future_event_type", "data": 42, "extra": "info"}
    event = parse_event(raw)
    assert event is raw  # exact same object, not a copy


def test_parse_extra_keys_ignored():
    """Extra keys in known event types must not raise — dataclass ignores them."""
    raw = {
        "type": "agent_start",
        "model": "claude-3",
        "session_id": "s1",
        "future_field": "ignored",
    }
    event = parse_event(raw)
    assert isinstance(event, AgentStartEvent)
    assert event.model == "claude-3"
