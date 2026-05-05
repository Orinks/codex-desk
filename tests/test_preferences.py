from __future__ import annotations

import pytest

from wxpi.preferences import AppPreferences, ThreadOptions, TranscriptPreferences


def test_default_preferences_keep_transcript_minimal():
    prefs = AppPreferences()

    assert prefs.personality == "none"
    assert prefs.transcript == TranscriptPreferences(
        show_tool_calls=False,
        show_reasoning=False,
        show_diagnostics=True,
        show_file_summaries=True,
    )


def test_thread_options_validate_known_values():
    options = ThreadOptions(
        model="gpt-5.4",
        reasoning_effort="high",
        sandbox="read-only",
        approval_policy="never",
        mode="worktree",
        base_branch="main",
    )

    assert options.reasoning_effort == "high"
    assert options.mode == "worktree"


def test_unknown_personality_is_rejected():
    with pytest.raises(ValueError, match="unknown personality"):
        AppPreferences(personality="chatty")


def test_unknown_thread_mode_is_rejected():
    with pytest.raises(ValueError, match="unknown thread mode"):
        ThreadOptions(mode="cloud")
