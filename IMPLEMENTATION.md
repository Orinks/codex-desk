# wxPi: Implementation Plan

## Guiding Principles

1. **Accessibility first** — screen reader support is baked in from day one, not retrofitted.
2. **Thin wrapper** — wxPi owns the UI layer; Pi owns everything below the JSONL interface.
3. **Testable bridge** — the RPC bridge is fully unit-testable without a live Pi process.
4. **One platform at a time** — get Windows + NVDA working well before expanding.
5. **Ship early** — a clunky-but-accessible MVP is better than a beautiful inaccessible beta.

---

## Milestone 0: Environment and Spike (1-2 days)

**Goal:** Prove the RPC bridge works from Python before writing any wx code.

### Tasks

- [ ] Set up dev environment: Python 3.11+, wxPython 4.2+, Node.js, Pi installed globally.
- [ ] Write `spike_rpc.py`: spawn Pi via `subprocess.Popen(['pi', '--mode', 'rpc'])`, read
      JSONL from stdout (binary mode, `readline()` on raw bytes), send a `prompt` command,
      print all events to console.
- [ ] Verify: streaming `message_update` events arrive as expected, `tool_execution_*` events
      fire for a `read` tool call, `agent_end` event fires after completion.
- [ ] Verify U+2028/U+2029 safety: send a prompt containing those characters, confirm the
      JSONL reader does not split incorrectly.
- [ ] Document Pi version tested against; pin it.

**Exit criterion:** Python script can drive a Pi session end-to-end over RPC with no wx involved.

---

## Milestone 1: Core RPC Bridge Module (3-5 days)

**Goal:** Production-quality RPC bridge that can be tested without wx.

### Deliverables

- `wxpi/rpc_bridge.py`: `PiBridge` class
  - `start(cwd, session_path=None, continue_session=False)` → spawns Pi subprocess.
  - `send_prompt(text, images=None)` → writes JSONL `prompt` command to stdin.
  - `send_abort()` → writes `abort` command.
  - `send_ui_response(request_id, result)` → handles `confirm`/`select`/`input` responses.
  - Background reader thread using `threading.Thread(daemon=True)`.
  - Event callback registry: `on_event(callback)` where callback receives parsed event dict.
  - Process death detection and `on_process_exit(callback)`.
  - Strict byte-level `readline()` — never decode before splitting.

- `wxpi/rpc_events.py`: typed dataclasses or TypedDict for each RPC event type.

- `tests/test_rpc_bridge.py`: unit tests using `subprocess.Popen` mock with a fake Pi
  (a simple Python script that emits test event sequences). No live Pi required for tests.

**Exit criterion:** `PiBridge` passes unit tests for happy path, abort, process death, and
UI interaction request/response cycle.

---

## Milestone 2: Minimal wx Shell (5-7 days)

**Goal:** A working single-session wx window that drives Pi and shows output.

### Deliverables

- `wxpi/app.py`: `wx.App` subclass, startup logic, working directory resolution.
- `wxpi/main_frame.py`: `wx.Frame` with:
  - `wx.TextCtrl` (read-only, rich) for transcript — top 80% of vertical space.
  - `wx.TextCtrl` (editable, multiline) for input — bottom 20%.
  - Status bar showing: model name, turn status, working directory.
  - Menu bar: File (New Session, Open Session, Change Workspace, Quit), Edit, View, Help.
- `wxpi/session_controller.py`: wires `PiBridge` events to transcript updates via
  `wx.CallAfter`. Owns the `PiBridge` instance.
- Transcript rendering: plain-text append, tool call blocks rendered as
  `[TOOL: bash | RUNNING]\n<output>\n[DONE: exit 0]`.
- Input: Enter submits, Shift+Enter inserts newline.
- Escape sends abort to Pi.

**Accessibility requirements at this milestone:**
- Transcript `wx.TextCtrl` must have `SetName("Transcript")` and correct role.
- Input `wx.TextCtrl` must have a visible label ("Message") and `wx.ID` for label association.
- All menu items must have accelerators.
- Tab order: input → transcript → session list (once added).

**Exit criterion:** User can type a prompt, see streaming response, see tool call block appear
and update, all without touching the mouse.

---

## Milestone 3: Tool Approval Dialog (2-3 days)

**Goal:** Safe, accessible tool approval flow.

### Deliverables

- `wxpi/approval_dialog.py`: `ToolApprovalDialog(wx.Dialog)`
  - Shows: tool name, command/args in mono-spaced read-only `wx.TextCtrl`.
  - Buttons: Deny (default focus, Escape), Allow (Enter), Allow All Session.
  - `wx.StaticText` label announces "Tool execution requires approval" as dialog title.
  - Keyboard: Tab cycles buttons, Enter activates focused button.
  - Strips `bash` from "Allow All Session" scope (hardcoded for safety).
- Integration: `SessionController` intercepts `confirm` RPC events, raises dialog modally,
  sends response via `PiBridge.send_ui_response()`.
- Allow-list store: in-memory dict per session, keyed by tool name.

**NVDA test:** Dialog must announce title and tool details when it opens. Deny button must
be announced as default. All buttons must be reachable by Tab.

**Exit criterion:** `bash ls /tmp` requires approval; dialog opens, keyboard works, response
sent correctly; `bash rm -rf /` triggers approval and can be denied.

---

## Milestone 4: Session Management (3-4 days)

**Goal:** Open, continue, and new sessions from the UI.

### Deliverables

- Session list: `wx.SplitterWindow` layout — left pane is `wx.ListCtrl` of sessions, right pane
  is transcript + input. Sessions loaded from `~/.pi/agent/sessions/` on startup.
- `wxpi/session_list_panel.py`: lists sessions by directory + timestamp, Enter opens selected.
- New session: `Ctrl+N` → `wx.DirDialog` → spawn new `PiBridge`.
- Continue: select session, Enter → spawn Pi with `--session <path> --continue`.
- Fork: `Ctrl+F` → send `fork` RPC command.
- Session lifecycle: stopping old `PiBridge`, starting new one, updating transcript panel.

**Exit criterion:** User can switch between sessions without restarting wxPi.

---

## Milestone 5: Accessibility Hardening — Windows + NVDA (5-7 days)

**Goal:** Full NVDA compatibility on Windows; establish the accessibility test baseline.

### Deliverables

- `wxpi/announcer.py`: `Announcer` class with `announce(text, priority)`.
  - Windows: `NotifyWinEvent` wrapper using `ctypes` + `comtypes` or a hidden
    `wx.TextCtrl` with UIA `LiveSetting` (research which is more reliable).
  - macOS/Linux: stubs for Phase 2.
- Announcements wired into `SessionController`:
  - "Turn started" → polite announce.
  - "Turn ended" → polite announce.
  - "Tool approval required: <tool name>" → assertive announce.
  - "Error: <message>" → assertive announce.
- Full NVDA manual test pass of all Milestone 1–4 flows. Document issues.
- Fix all NVDA issues found. Maintain a `ACCESSIBILITY_NOTES.md` with platform-specific findings.

**Exit criterion:** A NVDA user can complete a full coding session (prompt → response → tool
approval → result) without sighted assistance.

---

## Milestone 6: Packaging and Alpha Release (3-4 days)

**Goal:** Distributable Windows binary for alpha testers.

### Deliverables

- `build/windows/`: PyInstaller spec file producing a single `.exe` or directory bundle.
- Startup check: verify `pi` is on PATH; show friendly error dialog if not, with install link.
- `README.md`: install Pi, install wxPi, launch, first-run provider setup.
- Alpha release: internal only, 3-5 testers (screen reader users preferred).

**Exit criterion:** Tester with fresh Windows install can follow README, install Pi, install
wxPi, and complete a session without contacting Josh.

---

## Future Milestones (Not Scheduled)

- **Phase 2**: macOS/Linux packaging, VoiceOver/Orca testing, Announcer cross-platform,
  high-contrast theming, verbosity modes, focus management preferences.
- **Phase 3**: WebView transcript, markdown rendering, drag-and-drop, image attachments,
  model switching UI, workspace profiles, audit log viewer.
- **Phase 4**: Pi extension authoring from wxPi, session encryption, upstream contributions
  to Pi's accessibility story.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Pi RPC protocol changes | Medium | High | Pin version, bridge isolation, integration tests |
| macOS PATH for Node.js | High | Medium | Preferences "locate Pi binary" dialog |
| wx.TextCtrl streaming perf | Medium | Medium | Transcript length cap + load-earlier mechanism |
| Platform live announcement fragility | High | High | Invest early, document known gaps |
| WebView AT-SPI on Linux | High | Medium | Defer WebView to Phase 3; TextCtrl for MVP |
| "Allow All Session" security misuse | Low | High | Exclude bash, require explicit per-command approval |
