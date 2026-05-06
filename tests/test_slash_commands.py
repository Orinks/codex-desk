from __future__ import annotations

from codex_desk.slash_commands import (
    SLASH_COMMANDS,
    filter_slash_commands,
    parse_slash_command,
    unescape_literal_slash,
)


def test_filter_slash_commands_returns_all_for_empty_trigger():
    assert filter_slash_commands("/") == list(SLASH_COMMANDS)


def test_filter_slash_commands_matches_prefix_case_insensitively():
    assert [command.name for command in filter_slash_commands("/NEW")] == ["/new"]


def test_filter_slash_commands_matches_aliases():
    assert [command.name for command in filter_slash_commands("/cw")] == ["/workspace"]


def test_parse_slash_command_returns_command_and_args():
    match = parse_slash_command("/goal ship accessible slash commands")

    assert match is not None
    assert match.command.name == "/goal"
    assert match.command.supports_inline_args is True
    assert match.args == "ship accessible slash commands"


def test_codex_command_surface_includes_goal_and_status():
    names = {command.name for command in SLASH_COMMANDS}

    assert "/goal" in names
    assert "/status" in names
    assert "/compact" in names
    assert len(SLASH_COMMANDS) > 30


def test_parse_slash_command_ignores_plain_text_and_unknown_commands():
    assert parse_slash_command("please /settings") is None
    assert parse_slash_command("/does-not-exist") is None


def test_parse_slash_command_ignores_escaped_literal_slash():
    assert parse_slash_command("//settings") is None
    assert unescape_literal_slash("//settings") == "/settings"
