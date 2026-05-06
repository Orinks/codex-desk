"""Transcript formatting helpers."""

from __future__ import annotations

from codex_desk.preferences import TranscriptPreferences


def format_turn_details(model: str, reasoning_effort: str, state: str = "Current turn") -> str:
    """Return concise turn metadata for non-transcript UI surfaces."""
    return f"{state}: model {model}, reasoning effort {reasoning_effort}"


def format_turn_details_with_status(details: str, status: str) -> str:
    """Return turn metadata with current progress status for focusable UI surfaces."""
    return f"Status: {status}; {details}"


def format_user_prompt(text: str, preferences: TranscriptPreferences) -> str:
    """Return the transcript text appended when the user sends a prompt."""
    if preferences.speaker_labels == "role":
        return f"You: {text}\n\n"
    return f"{text}\n\n"


def format_assistant_prefix(preferences: TranscriptPreferences) -> str:
    """Return the transcript text appended when Codex starts answering."""
    if preferences.speaker_labels == "role":
        return "Assistant: "
    return ""


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
