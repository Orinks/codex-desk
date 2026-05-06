# Codex Desk Auth Integration Note

Status: research note based on the installed Pi package `@mariozechner/pi-coding-agent@0.61.0`

## Key Finding

Pi supports the browser-based OAuth flow we want, but not as a top-level `pi login`
CLI command and not as a documented RPC command.

In this installed build:

- OAuth login is exposed in interactive mode as `/login`
- The actual implementation lives in Pi's auth storage and OAuth provider code
- Pi persists credentials in `~/.pi/agent/auth.json`
- A plain `pi --mode rpc --no-session` process exits immediately when no models are
  available, which happens on a clean machine with no auth and no API keys

That means Codex Desk should not assume it can boot an unauthenticated RPC session and then
ask Pi to log in inside that same process.

## Recommendation

Use a dedicated auth bootstrap path above `PiBridge`.

1. Before starting the main RPC session, inspect `~/.pi/agent/auth.json` and/or run a
   lightweight Pi helper to determine whether any usable auth exists.
2. If not authenticated, launch a dedicated login helper subprocess that uses Pi's own
   auth APIs and reports progress back to wx.
3. After successful login, start the normal `pi --mode rpc` session and query
   `get_available_models`.

## Do Not Do

- Do not rely on a nonexistent `pi login` command.
- Do not treat `/login` as a stable RPC command path.
- Do not block the UI thread waiting for browser auth.
- Do not store provider credentials in Codex Desk-owned config.

## Minimal Seam To Add Later

Add an `AuthService` owned by app startup or the future session controller. Its job:

- inspect auth state
- launch/cancel login subprocess
- surface progress/status/error updates to wx
- notify the app when login completes so the main Pi RPC process can be started

`PiBridge` should remain transport-focused and should not absorb auth orchestration.
