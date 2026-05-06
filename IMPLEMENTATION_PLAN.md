# Codex Desk Implementation Plan

**Status:** Active MVP  
**Package manager:** UV  
**Frontend:** wxPython  
**Backend:** OpenAI Codex CLI app-server

## Guiding Principles

1. Build accessibly first: native controls, keyboard paths, readable transcript, explicit status.
2. Keep Codex integration isolated behind a small bridge.
3. Use TDD for bridge contracts and non-GUI logic.
4. Keep the default experience vanilla Codex.
5. Treat optional workflow systems as profiles, never hidden defaults.

## Milestone 1: Codex Bridge

Implemented:

- `src/codex_desk/codex_app_server_bridge.py`
- `tests/fake_codex_app_server.py`
- `tests/test_codex_app_server_bridge.py`

Acceptance:

- Starts `codex app-server`.
- Sends `initialize`, `initialized`, and `thread/start`.
- Sends `turn/start` with text input.
- Normalizes app-server notifications into UI events.
- Tests run without live Codex.

Next:

- Add more app-server notification mappings for tool calls, approvals, and errors.
- Add graceful stderr/error reporting when Codex fails to start.
- Wire real thread resume/listing once the stable app-server contract is confirmed.

## Milestone 2: Native Shell

Implemented:

- `src/codex_desk/app.py`
- `src/codex_desk/main_frame.py`
- `src/codex_desk/session_controller.py`
- `src/codex_desk/approval_dialog.py`

Next:

- Add visible labels immediately before transcript and prompt controls where wx/NVDA benefits.
- Add an explicit Send button for users who do not use Enter-to-submit.
- Add an accessible event/status log pane or command history.

## Milestone 3: Profiles

Implemented:

- `src/codex_desk/profiles.py`
- `src/codex_desk/profile_dialog.py`
- `tests/test_profiles.py`

Profiles:

- Vanilla Codex: installed by default.
- Oh My Codex: optional.
- Obra: optional placeholder until install contract is confirmed.
- Compound Engineering: optional placeholder until install contract is confirmed.

Next:

- Implement a profile installer interface.
- Confirm exact install commands for Obra and Compound Engineering before running anything.
- Add uninstall/disable state tracking.

## Milestone 4: First-Run

Implemented:

- Codex PATH check.
- npm install flow for `@openai/codex`.
- Manual setup link to official Codex CLI docs.

Next:

- Detect signed-in Codex state with a real lightweight Codex command.
- Surface authentication failures in plain language.
- Add a preferences field for custom Codex binary path.

## Milestone 5: Accessibility Hardening

Next:

- Manual NVDA pass on Windows.
- Document results in `ACCESSIBILITY_NOTES.md`.
- Add platform-specific notes for VoiceOver and Orca later.
- Add live announcements for turn start/end, approval required, errors, and disconnect.

## Verification

Current green gate:

```powershell
uv run pytest
```
