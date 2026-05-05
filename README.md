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
- First-run panel that can install `@openai/codex` with npm and point users to Codex sign-in.
- Agent profile registry and a native profile dialog.

Still early:

- Codex resume/thread listing is not wired yet.
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
- tool execution start/end events

The wx UI only consumes this normalized contract, keeping Codex protocol details isolated in
`src/wxpi/codex_app_server_bridge.py`.

wxAgent launches app-server with `analytics.enabled=false` so it does not inherit analytics
opt-ins from a user's main Codex profile. Known plugin marketplace and analytics `403` warnings
from Codex stderr are treated as debug diagnostics because they do not block app-server auth,
thread startup, or model execution. Unexpected stderr remains visible as a Codex warning.

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
