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
- Implemented bridge/profile code until tests passed.
- Kept the old bridge regression tests passing.

## Current Test Command

```powershell
uv run pytest
```

## Remaining Risks

- Codex app-server protocol coverage is still narrow.
- Thread resume and session browsing are not implemented.
- Profile install commands for Obra and Compound Engineering are placeholders until verified.
- GUI accessibility still needs live NVDA verification.
