from __future__ import annotations

from wxpi.rpc_events import MessageUpdateEvent, TurnEndEvent, TurnStartEvent
from wxpi.session_controller import SessionController


class FakeMainFrame:
    def __init__(self) -> None:
        self.transcript: list[str] = []

    def append_transcript(self, text: str) -> None:
        self.transcript.append(text)

    def stop_working_status(self, status: str = "Idle") -> None:
        self.status = status


def test_completed_messages_get_paragraph_spacing_without_extra_turn_gap():
    frame = FakeMainFrame()
    controller = SessionController(frame)

    controller._on_turn_start(TurnStartEvent())
    controller._on_message_update(MessageUpdateEvent(delta="First message.", completed=True))
    controller._on_message_update(MessageUpdateEvent(delta="Second message.", completed=True))
    controller._on_turn_end(TurnEndEvent())

    assert "".join(frame.transcript) == "First message.\n\nSecond message.\n\n"


def test_streaming_messages_keep_existing_delta_behavior():
    frame = FakeMainFrame()
    controller = SessionController(frame)

    controller._on_turn_start(TurnStartEvent())
    controller._on_message_update(MessageUpdateEvent(delta="Hello "))
    controller._on_message_update(MessageUpdateEvent(delta="world"))
    controller._on_turn_end(TurnEndEvent())

    assert "".join(frame.transcript) == "Hello world\n\n"
