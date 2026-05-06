"""
Typed dataclasses for each Pi RPC event type.

parse_event() converts a raw dict (from JSONL) into the appropriate dataclass.
Unknown event types are returned as-is for forward compatibility.
"""
import dataclasses
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class AgentStartEvent:
    type: str = "agent_start"
    model: str = ""
    session_id: str = ""


@dataclass
class MessageUpdateEvent:
    type: str = "message_update"
    delta: str = ""
    completed: bool = False


@dataclass
class ReasoningUpdateEvent:
    type: str = "reasoning_update"
    delta: str = ""


@dataclass
class FileChangeSummaryEvent:
    type: str = "file_change_summary"
    created: int = 0
    edited: int = 0
    deleted: int = 0


@dataclass
class TurnStartEvent:
    type: str = "turn_start"
    turn_id: str = ""


@dataclass
class TurnEndEvent:
    type: str = "turn_end"
    turn_id: str = ""


@dataclass
class ToolExecutionStartEvent:
    type: str = "tool_execution_start"
    tool: str = ""
    args: Any = None
    request_id: str = ""


@dataclass
class ToolExecutionEndEvent:
    type: str = "tool_execution_end"
    status: str = ""
    exit_code: Optional[int] = None


@dataclass
class ConfirmEvent:
    type: str = "confirm"
    id: str = ""
    tool: str = ""
    args: Any = None
    cwd: str = ""


@dataclass
class AgentEndEvent:
    type: str = "agent_end"


@dataclass
class DiagnosticEvent:
    type: str = "diagnostic"
    severity: str = "warning"
    message: str = ""


_EVENT_MAP = {
    "agent_start": AgentStartEvent,
    "message_update": MessageUpdateEvent,
    "reasoning_update": ReasoningUpdateEvent,
    "file_change_summary": FileChangeSummaryEvent,
    "turn_start": TurnStartEvent,
    "turn_end": TurnEndEvent,
    "tool_execution_start": ToolExecutionStartEvent,
    "tool_execution_end": ToolExecutionEndEvent,
    "confirm": ConfirmEvent,
    "agent_end": AgentEndEvent,
    "diagnostic": DiagnosticEvent,
}


def parse_event(raw: dict):
    """Convert a raw event dict to a typed dataclass.

    Unknown event types are returned unchanged (forward compatibility).
    Extra keys in known types are silently ignored.
    """
    cls = _EVENT_MAP.get(raw.get("type", ""))
    if cls is None:
        return raw
    known = {f.name for f in dataclasses.fields(cls)}
    kwargs = {k: v for k, v in raw.items() if k in known}
    return cls(**kwargs)
