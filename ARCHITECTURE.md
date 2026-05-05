# wxAgent Architecture

## Overview

wxAgent is a native wxPython desktop app that wraps the local OpenAI Codex CLI/app-server. The app
is designed for screen reader and keyboard users first.

```text
wxAgent wxPython UI
  -> SessionController
  -> CodexAppServerBridge
  -> codex app-server
  -> Codex-authenticated local agent runtime
```

## Integration Boundary

The bridge starts:

```powershell
codex app-server
```

Codex app-server speaks JSON-RPC messages over newline-delimited JSON on stdio. wxAgent sends:

- `initialize`
- `initialized`
- `thread/start`
- `turn/start`

The bridge currently normalizes supported app-server messages into these internal event types:

- `agent_start`
- `turn_start`
- `message_update`
- `turn_end`
- `diagnostic`
- `reasoning_update`
- `file_change_summary`

`thread/start` is parameterized from native session controls: working directory, model,
personality, sandbox mode, and approval policy. `turn/start` carries the selected reasoning effort.
Cloud execution is not currently exposed because this app talks directly to the local Codex
app-server process.

Future Codex protocol work belongs inside `CodexAppServerBridge`, not in the wx widgets.

## UI Layers

- `app.py`: startup, Codex PATH check, first-run routing.
- `main_frame.py`: transcript, prompt input, menus, status bar.
- `session_controller.py`: bridge lifecycle and event dispatch through `wx.CallAfter`.
- `new_session_dialog.py`: model, reasoning, sandbox, branch, and local/worktree session choices.
- `settings_dialog.py`: global personality and transcript verbosity preferences.
- `mcp_manager_dialog.py`: native MCP server lifecycle management backed by `codex mcp`.
- `approval_dialog.py`: keyboard-first tool approval dialog.
- `profile_dialog.py`: read-only profile discovery for optional workflow packs.

## Transcript Policy

The default transcript is intentionally minimal: what the user wrote, what the assistant said,
warnings that may require attention, and a concise file summary when Codex reports file changes.
Tool-call blocks and reasoning summaries are configurable in settings so power users can opt into
more process detail without making the composer busy.

## Workspaces

New sessions can run in the selected folder directly or in a detached Git worktree created under
`~/.codex/worktrees`. The branch picker defaults to the current branch when the selected folder is a
Git repository.

## MCP Servers

wxAgent delegates MCP lifecycle operations to the Codex CLI:

- `codex mcp list`
- `codex mcp add`
- `codex mcp remove`
- `codex mcp login`
- `codex mcp logout`

This keeps wxAgent aligned with Codex auth and config behavior while still giving screen reader
users a native control surface.

## Accessibility Rules

- Use native wx controls.
- Use sizers, not absolute positioning.
- Keep all actions keyboard reachable.
- Put visible labels immediately before inputs where practical.
- Use `wx.CallAfter` for all UI updates from background bridge callbacks.
- Treat screen reader testing as a release gate, not polish.

## Profiles

Profiles describe optional capability packs. Vanilla Codex is the only default. Oh My Codex, Obra,
and Compound Engineering are opt-in and should not install until the user explicitly chooses them.

## Testing

Backend and profile behavior is tested without live Codex through fake subprocesses. GUI behavior is
kept thin and should be verified manually with NVDA before alpha release.
