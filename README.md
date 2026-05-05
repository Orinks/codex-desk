# wxAgent

Native, screen-reader-first desktop control plane for the OpenAI Codex CLI.

wxAgent is a wxPython app that gives Codex a native accessible frontend: a transcript, prompt
input, workspace controls, status updates, approval dialogs, and optional capability profiles.
The default profile is intentionally vanilla Codex. Extra workflow packs such as Oh My Codex,
Obra, and Compound Engineering are modeled as opt-in profiles.

## Current Status

This repo is in early MVP implementation.

Implemented:

- UV-managed Python project.
- Codex app-server bridge over JSONL/JSON-RPC.
- Per-launch Codex analytics opt-out plus filtering for known non-fatal plugin/analytics 403
  warnings.
- Deterministic fake Codex app-server tests, so bridge behavior is tested without live Codex.
- wxPython shell with transcript, prompt input, menus, status bar, and approval dialog plumbing.
- Native settings for Codex personality and transcript verbosity.
- New session options for model, reasoning effort, sandbox, approval policy, local workspace, and
  Git worktree-backed sessions.
- Main-window model and reasoning controls so users can change the next turn without reopening a
  session dialog.
- Native MCP server manager for listing, adding, removing, logging in, and logging out through
  `codex mcp`.
- Native Codex plugin manager for marketplace add/upgrade/remove and plugin enable/disable.
- First-run panel that can install `@openai/codex` with npm and point users to Codex sign-in.
- Agent profile registry and a native profile dialog.

Still early:

- Codex resume/thread listing is not wired yet.
- Cloud task execution is not exposed; wxAgent currently starts local Codex app-server threads only.
- Tool approval mapping uses the app's internal normalized event contract and needs live Codex
  protocol hardening.
- NVDA/manual accessibility testing still needs a documented pass.
- The old Pi bridge remains under test as legacy scaffold code until the Codex path fully replaces it.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Node.js/npm for installing Codex from npm
- OpenAI Codex CLI: `npm i -g @openai/codex`

The first Codex run prompts for ChatGPT/API authentication:

```powershell
codex
```

## Development

```powershell
uv sync
uv run pytest
uv run wxagent
```

The package is still named `wxpi` internally from the original scaffold. Product-facing naming is
now `wxAgent`; a later cleanup can rename the Python package once the Codex bridge has settled.

## Architecture

wxAgent talks to Codex through `codex app-server`, which exposes JSON-RPC messages over JSONL
stdio. The bridge normalizes Codex app-server messages into a small UI event contract:

- `agent_start`
- `turn_start`
- `message_update`
- `turn_end`
- `confirm`
- `diagnostic`
- `reasoning_update`
- `file_change_summary`
- tool execution start/end events

The wx UI only consumes this normalized contract, keeping Codex protocol details isolated in
`src/wxpi/codex_app_server_bridge.py`.

wxAgent launches app-server with `analytics.enabled=false` so it does not inherit analytics
opt-ins from a user's main Codex profile. Known plugin marketplace and analytics `403` warnings
from Codex stderr are treated as debug diagnostics because they do not block app-server auth,
thread startup, or model execution. Unexpected stderr remains visible as a Codex warning.

Personality is configured in `Edit -> Settings`, not in the composer. Transcript settings default
to a quiet view without speaker prefixes: user prompts, assistant text, and concise file summaries
such as `Created 1 file, edited 2 files.` `You` / `Assistant` speaker labels, tool calls, and
reasoning summaries are opt-in.
Codex diagnostics are also opt-in because app-server can emit noisy non-fatal plugin and shell
setup messages that are not useful in the main conversation transcript.

The main window and session dialogs use visible labels before edit boxes and combo boxes for screen
reader compatibility. Accessibility verification steps live in
`docs/accessibility-test-plan.md`.

MCP servers are managed from `Tools -> MCP Servers`. wxAgent shells out to the Codex CLI for the
supported lifecycle commands rather than editing MCP entries by hand.

Codex plugins are managed from `Tools -> Codex Plugins`. Marketplace lifecycle operations use
`codex plugin marketplace`; plugin enable/disable toggles update the user's Codex config with a
backup because the current CLI exposes marketplace commands but not a dedicated plugin toggle
command.

## Test Strategy

TDD is the default workflow:

1. Add a fake backend or pure unit test.
2. Watch it fail.
3. Implement the smallest production code that makes it pass.
4. Update docs in the same turn.

Current verification:

```powershell
uv run pytest
```
