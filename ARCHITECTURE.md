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

Future Codex protocol work belongs inside `CodexAppServerBridge`, not in the wx widgets.

## UI Layers

- `app.py`: startup, Codex PATH check, first-run routing.
- `main_frame.py`: transcript, prompt input, menus, status bar.
- `session_controller.py`: bridge lifecycle and event dispatch through `wx.CallAfter`.
- `approval_dialog.py`: keyboard-first tool approval dialog.
- `profile_dialog.py`: read-only profile discovery for optional workflow packs.

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
