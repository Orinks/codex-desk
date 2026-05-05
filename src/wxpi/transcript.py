"""Transcript formatting helpers."""

from __future__ import annotations

from wxpi.preferences import TranscriptPreferences


def format_file_summary(created: int = 0, edited: int = 0, deleted: int = 0) -> str:
    """Return a concise human-readable file change summary."""
    parts = []
    if created:
        parts.append(_plural(created, "created", "file"))
    if edited:
        parts.append(_plural(edited, "edited", "file"))
    if deleted:
        parts.append(_plural(deleted, "deleted", "file"))
    if not parts:
        return "No file changes."
    return ", ".join(parts).capitalize() + "."


def should_show_event(event_type: str, preferences: TranscriptPreferences) -> bool:
    """Return whether a normalized event should appear in the transcript."""
    if event_type in {"tool_execution_start", "tool_execution_end"}:
        return preferences.show_tool_calls
    if event_type == "reasoning_update":
        return preferences.show_reasoning
    if event_type == "diagnostic":
        return preferences.show_diagnostics
    if event_type == "file_change_summary":
        return preferences.show_file_summaries
    return True


def _plural(count: int, verb: str, noun: str) -> str:
    suffix = "" if count == 1 else "s"
    return f"{verb} {count} {noun}{suffix}"
