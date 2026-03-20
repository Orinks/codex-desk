# Should Josh Build on Pi?

## Recommendation: Yes, with one important caveat.

### The case FOR building on Pi

**1. RPC is purpose-built for this use case.**
Pi's `--mode rpc` interface is documented explicitly for "IDE integration, custom frontends, and
automation workflows." It is bidirectional, streaming, supports tool approval hooks, and handles
session management. This is not an incidental feature — it's a first-class integration path.
Building a custom frontend is exactly what the RPC mode was designed to enable.

**2. Pi handles the hard LLM plumbing.**
Multi-provider support (15+ providers), OAuth flows for Claude Pro/Max and other subscription
services, session persistence with tree branching, context compaction — these are all solved
problems inside Pi. Building them from scratch in Python would be months of work and would
perpetually lag behind upstream provider API changes.

**3. The surface area Josh needs to own is well-defined and small.**
wxPi only needs to own: the wx UI layer, the JSONL subprocess bridge, tool approval dialogs,
accessibility infrastructure, and packaging. Everything below that is Pi's problem.

**4. Session model is robust.**
JSONL tree sessions with fork/branch/compact are more sophisticated than a typical "conversation
history array." Starting fresh would mean rebuilding this — or accepting a worse user experience.

**5. The extension system is a future superpower.**
Once the core is built, Pi's TypeScript extension system allows dropping custom tools, custom
commands, and custom approval logic into the Pi process without changing wxPi. Josh can ship
accessibility-specific extensions (e.g., a verbosity controller extension, a braille-output
extension) without touching the UI layer.

---

### The caveat: Josh does NOT control Pi's release cadence.

Pi is a third-party project. If the RPC protocol changes between versions, wxPi breaks. Mitigation:

- Pin the Pi version in wxPi's requirements/setup docs.
- Write an integration test suite that exercises the RPC protocol against the pinned version.
- Monitor Pi's changelog for breaking RPC changes.
- Keep the RPC bridge isolated in a single module (`rpc_bridge.py`) so that protocol changes
  are localized to one file.

This is an acceptable dependency risk for the value Pi provides. It is similar to depending on
any CLI tool (e.g., `git`) from a GUI wrapper — manageable with version pinning and a thin
abstraction layer.

---

### What Josh should NOT do

- **Do not fork Pi.** Maintaining a fork to add accessibility hooks is a maintenance nightmare.
  The RPC protocol already provides the hooks needed. If something is genuinely missing, contribute
  it upstream or use the extension system.

- **Do not use Pi's interactive mode and screen-scrape it.** This approach (pty-based screen
  scraping of the TUI) is fragile, inaccessible, and explicitly wrong. RPC is the answer.

- **Do not roll a custom LLM client in Python instead.** The temptation to "just use anthropic-sdk"
  directly is understandable but underestimates the scope: session management, multi-provider
  routing, compaction, the extension system — these are all features that would need to be rebuilt.
  Unless Josh wants wxPi to be an Anthropic-only client (which removes the OAuth/multi-provider
  story entirely), Pi is a better base.

---

### Short verdict

Build on Pi. Own the wx layer. Let Pi own the LLM layer. The RPC interface is clean, the
session model is solid, and the tool approval hooks are exactly what's needed for a safe,
accessible tool call UX. The dependency risk is real but manageable.
