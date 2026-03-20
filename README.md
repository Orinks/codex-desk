# wxPi Architecture Research

Architecture document for a proposed native accessible wxPython frontend wrapping the
[Pi coding agent](https://shittycodingagent.ai) (`badlogic/pi-mono`) as the backend runtime.

## Documents

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Full system design covering RPC integration,
  session model, tool approval UX, accessibility architecture, file handling, error behavior,
  platform concerns, security, and MVP phasing.

- **[RECOMMENDATION.md](RECOMMENDATION.md)** — Should Josh build on Pi? Yes/no with reasoning.

- **[IMPLEMENTATION.md](IMPLEMENTATION.md)** — First milestones with concrete deliverables
  and exit criteria.

## Summary

**Integration approach:** Pi `--mode rpc` (JSONL over subprocess stdin/stdout).

**UI toolkit:** wxPython 4.2+, native widgets, platform accessibility APIs.

**MVP scope:** Single-session window, streaming transcript (`wx.TextCtrl`), tool approval
dialog, keyboard navigation, screen reader tested on Windows + NVDA.

**Dependency strategy:** Pin Pi version, isolate the RPC bridge in one module,
monitor upstream changelog.
