"""Slash command registry and parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SlashCommand:
    name: str
    summary: str
    usage: str
    action: str
    aliases: tuple[str, ...] = ()
    supports_inline_args: bool = False

    @property
    def tokens(self) -> tuple[str, ...]:
        return (self.name, *self.aliases)


@dataclass(frozen=True)
class SlashCommandMatch:
    command: SlashCommand
    args: str


SLASH_COMMANDS: tuple[SlashCommand, ...] = (
    SlashCommand(
        name="/model",
        summary="Choose what model and reasoning effort to use.",
        usage="/model",
        action="codex",
    ),
    SlashCommand(
        name="/fast",
        summary="Toggle Fast mode to enable fastest inference with increased plan usage.",
        usage="/fast",
        action="codex",
        supports_inline_args=True,
    ),
    SlashCommand(
        name="/ide",
        summary="Include current selection, open files, and other context from your IDE.",
        usage="/ide",
        action="codex",
        supports_inline_args=True,
    ),
    SlashCommand(
        name="/permissions",
        summary="Choose what Codex is allowed to do.",
        usage="/permissions",
        action="codex",
    ),
    SlashCommand(
        name="/keymap",
        summary="Remap TUI shortcuts.",
        usage="/keymap",
        action="codex",
        supports_inline_args=True,
    ),
    SlashCommand(
        name="/vim",
        summary="Toggle Vim mode for the composer.",
        usage="/vim",
        action="codex",
    ),
    SlashCommand(
        name="/setup-default-sandbox",
        summary="Set up elevated agent sandbox.",
        usage="/setup-default-sandbox",
        action="codex",
    ),
    SlashCommand(
        name="/sandbox-add-read-dir",
        summary="Let sandbox read a directory.",
        usage="/sandbox-add-read-dir <path>",
        action="codex",
        supports_inline_args=True,
    ),
    SlashCommand(
        name="/experimental",
        summary="Toggle experimental features.",
        usage="/experimental",
        action="codex",
    ),
    SlashCommand(
        name="/approve",
        summary="Approve one retry of a recent auto-review denial.",
        usage="/approve",
        action="codex",
    ),
    SlashCommand(
        name="/memories",
        summary="Configure memory use and generation.",
        usage="/memories",
        action="codex",
    ),
    SlashCommand(
        name="/skills",
        summary="Use skills to improve how Codex performs specific tasks.",
        usage="/skills",
        action="codex",
    ),
    SlashCommand(
        name="/hooks",
        summary="View and manage lifecycle hooks.",
        usage="/hooks",
        action="codex",
    ),
    SlashCommand(
        name="/review",
        summary="Review current changes and find issues.",
        usage="/review [instructions]",
        action="codex",
        supports_inline_args=True,
    ),
    SlashCommand(
        name="/rename",
        summary="Rename the current thread.",
        usage="/rename <title>",
        action="codex",
        supports_inline_args=True,
    ),
    SlashCommand(
        name="/new",
        summary="Start a new chat during a conversation.",
        usage="/new",
        action="new_session",
    ),
    SlashCommand(
        name="/resume",
        summary="Resume a saved chat.",
        usage="/resume [query]",
        action="codex",
        supports_inline_args=True,
    ),
    SlashCommand(
        name="/fork",
        summary="Fork the current chat.",
        usage="/fork",
        action="codex",
    ),
    SlashCommand(
        name="/init",
        summary="Create an AGENTS.md file with instructions for Codex.",
        usage="/init",
        action="codex",
    ),
    SlashCommand(
        name="/compact",
        summary="Summarize conversation to prevent hitting the context limit.",
        usage="/compact",
        action="codex",
    ),
    SlashCommand(
        name="/plan",
        summary="Switch to Plan mode.",
        usage="/plan [objective]",
        action="codex",
        supports_inline_args=True,
    ),
    SlashCommand(
        name="/goal",
        summary="Set or view the goal for a long-running task.",
        usage="/goal [objective]",
        action="codex",
        supports_inline_args=True,
    ),
    SlashCommand(
        name="/collab",
        summary="Change collaboration mode.",
        usage="/collab",
        action="codex",
    ),
    SlashCommand(
        name="/agent",
        summary="Switch the active agent thread.",
        usage="/agent",
        action="codex",
    ),
    SlashCommand(
        name="/side",
        summary="Start a side conversation in an ephemeral fork.",
        usage="/side [prompt]",
        action="codex",
        supports_inline_args=True,
    ),
    SlashCommand(
        name="/copy",
        summary="Copy last response as markdown.",
        usage="/copy",
        action="codex",
    ),
    SlashCommand(
        name="/raw",
        summary="Toggle raw scrollback mode for copy-friendly terminal selection.",
        usage="/raw [mode]",
        action="codex",
        supports_inline_args=True,
    ),
    SlashCommand(
        name="/diff",
        summary="Show git diff, including untracked files.",
        usage="/diff",
        action="codex",
    ),
    SlashCommand(
        name="/mention",
        summary="Mention a file.",
        usage="/mention",
        action="codex",
    ),
    SlashCommand(
        name="/status",
        summary="Show current session configuration and token usage.",
        usage="/status",
        action="codex",
    ),
    SlashCommand(
        name="/debug-config",
        summary="Show config layers and requirement sources for debugging.",
        usage="/debug-config",
        action="codex",
    ),
    SlashCommand(
        name="/title",
        summary="Configure which items appear in the terminal title.",
        usage="/title",
        action="codex",
    ),
    SlashCommand(
        name="/statusline",
        summary="Configure which items appear in the status line.",
        usage="/statusline",
        action="codex",
    ),
    SlashCommand(
        name="/theme",
        summary="Choose a syntax highlighting theme.",
        usage="/theme",
        action="codex",
    ),
    SlashCommand(
        name="/workspace",
        summary="Change workspace or start a worktree-backed session.",
        usage="/workspace",
        action="change_workspace",
        aliases=("/cwd",),
    ),
    SlashCommand(
        name="/settings",
        summary="Open Codex Desk settings.",
        usage="/settings",
        action="settings",
    ),
    SlashCommand(
        name="/profiles",
        summary="Open agent profile options.",
        usage="/profiles",
        action="profiles",
    ),
    SlashCommand(
        name="/plugins",
        summary="Browse plugins.",
        usage="/plugins",
        action="plugins",
    ),
    SlashCommand(
        name="/mcp",
        summary="List configured MCP tools; use /mcp verbose for details.",
        usage="/mcp [verbose]",
        action="mcp_servers",
        supports_inline_args=True,
    ),
    SlashCommand(
        name="/apps",
        summary="Manage apps.",
        usage="/apps",
        action="codex",
    ),
    SlashCommand(
        name="/logout",
        summary="Log out of Codex.",
        usage="/logout",
        action="codex",
    ),
    SlashCommand(
        name="/help",
        summary="Show available Codex Desk slash commands.",
        usage="/help",
        action="slash_help",
    ),
    SlashCommand(
        name="/quit",
        summary="Exit Codex.",
        usage="/quit",
        action="quit",
        aliases=("/exit",),
    ),
    SlashCommand(
        name="/feedback",
        summary="Send logs to maintainers.",
        usage="/feedback",
        action="codex",
    ),
    SlashCommand(
        name="/ps",
        summary="List background terminals.",
        usage="/ps",
        action="codex",
    ),
    SlashCommand(
        name="/stop",
        summary="Stop all background terminals.",
        usage="/stop",
        action="codex",
        aliases=("/clean",),
    ),
    SlashCommand(
        name="/clear",
        summary="Clear the terminal and start a new chat.",
        usage="/clear",
        action="codex",
    ),
    SlashCommand(
        name="/personality",
        summary="Choose a communication style for Codex.",
        usage="/personality",
        action="codex",
    ),
    SlashCommand(
        name="/realtime",
        summary="Toggle realtime voice mode.",
        usage="/realtime",
        action="codex",
    ),
)


def filter_slash_commands(query: str, commands: tuple[SlashCommand, ...] = SLASH_COMMANDS) -> list[SlashCommand]:
    """Return slash commands matching a typed command prefix."""
    normalized = query.strip().casefold()
    if not normalized or normalized == "/":
        return list(commands)
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    return [
        command
        for command in commands
        if any(token.casefold().startswith(normalized) for token in command.tokens)
    ]


def parse_slash_command(text: str, commands: tuple[SlashCommand, ...] = SLASH_COMMANDS) -> SlashCommandMatch | None:
    """Parse text that begins with a known slash command."""
    stripped = text.strip()
    if not stripped.startswith("/") or stripped.startswith("//"):
        return None
    token, _, args = stripped.partition(" ")
    normalized = token.casefold()
    for command in commands:
        if any(normalized == candidate.casefold() for candidate in command.tokens):
            return SlashCommandMatch(command=command, args=args.strip())
    return None


def unescape_literal_slash(text: str) -> str:
    """Return a literal prompt for text escaped with a doubled leading slash."""
    stripped = text.strip()
    if stripped.startswith("//"):
        return stripped[1:]
    return stripped
