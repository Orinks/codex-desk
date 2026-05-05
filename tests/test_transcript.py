from __future__ import annotations

from wxpi.preferences import TranscriptPreferences
from wxpi.transcript import format_file_summary, should_show_event


def test_format_file_summary_reports_only_changed_counts():
    assert format_file_summary(created=1, edited=2) == "Created 1 file, edited 2 files."


def test_format_file_summary_handles_no_changes():
    assert format_file_summary() == "No file changes."


def test_minimal_transcript_hides_process_noise():
    preferences = TranscriptPreferences()

    assert not should_show_event("tool_execution_start", preferences)
    assert not should_show_event("tool_execution_end", preferences)
    assert not should_show_event("reasoning_update", preferences)
    assert should_show_event("message_update", preferences)
    assert should_show_event("file_change_summary", preferences)


def test_transcript_preferences_can_show_tool_and_reasoning_detail():
    preferences = TranscriptPreferences(show_tool_calls=True, show_reasoning=True)

    assert should_show_event("tool_execution_start", preferences)
    assert should_show_event("reasoning_update", preferences)
