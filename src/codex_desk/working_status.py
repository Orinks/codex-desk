"""Helpers for Codex turn progress status text."""

from __future__ import annotations


def format_working_status(elapsed_seconds: int) -> str:
    """Return desktop-style working text for an active Codex turn."""
    elapsed_seconds = max(0, elapsed_seconds)
    minutes, seconds = divmod(elapsed_seconds, 60)
    if minutes:
        minute_label = "minute" if minutes == 1 else "minutes"
        second_label = "second" if seconds == 1 else "seconds"
        return f"Working for {minutes} {minute_label} {seconds} {second_label}"

    second_label = "second" if elapsed_seconds == 1 else "seconds"
    return f"Working for {elapsed_seconds} {second_label}"
