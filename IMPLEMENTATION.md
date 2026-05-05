# wxAgent Implementation Notes

## What Exists

wxAgent currently has two backend layers:

- `CodexAppServerBridge`: active MVP bridge for `codex app-server`.
- `PiBridge`: legacy scaffold bridge retained temporarily with tests so we do not lose known-good
  subprocess/JSONL behavior during the migration.

The active UI path uses `CodexAppServerBridge` through `SessionController`.

## TDD Work Completed

- Added failing tests for Codex app-server handshake and turn start.
- Added fake Codex app-server process for deterministic JSONL tests.
- Added failing tests for optional profile discovery.
- Added stderr diagnostic classification so known non-fatal Codex plugin/analytics `403` warnings
  stay out of the transcript while unexpected startup errors remain visible.
- Added preference tests and native settings for Codex personality plus transcript verbosity.
- Added worktree tests and helpers for branch-based detached Git workspaces.
- Added bridge tests for session options and concise file-change summaries.
- Added `codex mcp` service tests and a native MCP server manager dialog.
- Added `codex plugin marketplace` service tests and a native Codex plugin manager dialog.
- Added main-window model/reasoning selectors, Codex model cache loading, `auto_review` approval
  reviewer support, and a reusable accessibility test plan.
- Hid diagnostics by default and downgraded known non-fatal Codex plugin/shell snapshot stderr
  messages so they do not clutter the transcript.
- Implemented bridge/profile code until tests passed.
- Kept the old bridge regression tests passing.

## Current Test Command

```powershell
uv run pytest
```

## Remaining Risks

- Codex app-server protocol coverage is still narrow.
- Thread resume and session browsing are not implemented.
- File-change summaries use defensive normalization and need live app-server event hardening once
  Codex exposes the exact item shape across more tool paths.
- MCP list parsing follows the current CLI table output; a future Codex JSON list mode would be a
  better long-term interface if it becomes available.
- Plugin enable/disable is direct config editing because Codex exposes marketplace lifecycle
  commands but not a dedicated plugin toggle command.
- Profile install commands for Obra and Compound Engineering are placeholders until verified.
- GUI accessibility still needs live NVDA verification.
