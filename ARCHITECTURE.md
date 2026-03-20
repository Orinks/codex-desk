# wxPi: Native Accessible wxPython Frontend for Pi Coding Agent
## Architecture Document — March 2026

**Author:** Eli (Dev Lead / Systems Architect)
**Status:** Pre-implementation research sketch
**Audience:** Engineering decision-makers, Josh (lead implementer)

---

## 1. System Overview

wxPi is a proposed native desktop application — built with wxPython — that provides a fully accessible,
keyboard-driven UI shell around the Pi coding agent (`badlogic/pi-mono`). Pi handles all LLM interaction,
tool execution, session management, and provider auth. wxPi handles everything the user sees and touches:
panels, transcript rendering, tool approval dialogs, focus management, and screen reader integration.

```
┌──────────────────────────────────────────────────────────────┐
│                        wxPi Process                          │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────┐  │
│  │  Session     │  │  Transcript    │  │  Tool Approval  │  │
│  │  Manager     │  │  Panel (wx)    │  │  Dialogs (wx)   │  │
│  └──────┬───────┘  └───────┬────────┘  └────────┬────────┘  │
│         │                  │                    │            │
│         └──────────────────┴────────────────────┘            │
│                            │                                 │
│                    ┌───────▼────────┐                        │
│                    │  RPC Bridge    │                        │
│                    │  (subprocess + │                        │
│                    │  JSONL reader) │                        │
│                    └───────┬────────┘                        │
└────────────────────────────│─────────────────────────────────┘
                             │ stdin/stdout (JSONL)
                    ┌────────▼────────┐
                    │   pi --mode rpc │  (Node.js process)
                    │  (Pi runtime)   │
                    └─────────────────┘
```

Pi is spawned as a child process. Communication is strictly over stdin/stdout JSONL. wxPi is the
host process; Pi is a managed subprocess.

---

## 2. RPC vs. SDK vs. Print/JSON Mode

Pi offers four integration surfaces. Here is why RPC is the correct choice for wxPi:

### 2.1 Option Comparison

| Mode        | How it works                        | Suitability for wxPi         |
|-------------|-------------------------------------|------------------------------|
| Interactive | Full terminal TUI (ncurses-like)    | Unusable — terminal-specific |
| Print/JSON  | `pi -p "query"` → one-shot stdout   | Scripting only, no streaming |
| RPC         | `pi --mode rpc`, JSONL stdin/stdout  | **Best fit** — bidirectional, streaming, event-driven |
| SDK (Node)  | TypeScript/Node.js embedding        | Requires Node in Python proc; wrong language boundary |

### 2.2 Why RPC

- **Language boundary**: Pi is Node.js/TypeScript; wxPi is Python. Embedding the SDK requires running
  V8 inside a Python process (e.g., via `node` bridge) — a fragile, unsupported path. RPC is the
  designed cross-language interface.
- **Streaming events**: RPC delivers real-time `message_update` deltas, `tool_execution_*` events,
  and bidirectional UI requests. Print/JSON is fire-and-forget.
- **Tool approval**: RPC supports a bidirectional sub-protocol where Pi can send a `confirm` /
  `select` / `input` request and wait for the UI's response before proceeding. This is essential for
  surfacing tool approval dialogs.
- **Session continuity**: RPC process stays alive across turns; Print/JSON spawns a new process per
  query.
- **Official intent**: RPC is documented as "suitable for IDE integration, custom frontends, and
  automation workflows." This is exactly our use case.

### 2.3 RPC Protocol Specifics (Critical Details)

- JSONL over stdin/stdout: one JSON object per line, `\n`-delimited.
- **MUST split on `\n` only** — do not use `readline` or any reader that treats U+2028/U+2029
  as line separators. Python's `io.BufferedReader.readline()` is safe (byte-level `0x0A` split).
- Commands sent to Pi stdin: `prompt`, `steer`, `follow_up`, `abort`, model switching, session ops.
- Events streamed from Pi stdout: `agent_start`, `agent_end`, `turn_start`, `turn_end`,
  `message_update` (with streaming text delta), `tool_execution_start`, `tool_execution_update`,
  `tool_execution_end`, `extension_error`.
- UI interaction requests (bidirectional): `confirm`, `select`, `input`, `editor` — Pi sends
  these and blocks until wxPi sends a response.

---

## 3. Auth / OAuth Implications

### 3.1 Pi Handles Auth — wxPi Does Not

Pi manages all provider credentials: OAuth flows (Claude Pro/Max, ChatGPT Plus/Pro, GitHub Copilot,
Gemini), API keys, and the `models.json` config. wxPi does not store credentials; it inherits Pi's
auth state from `~/.pi/`.

### 3.2 OAuth UX Challenge

OAuth flows that require browser-based login (e.g., Claude Pro/Max) are initiated inside Pi and
open the system browser. Pi emits a URL or status notification via RPC. wxPi must:
1. Display the URL / status to the user (accessible announcement via screen reader).
2. Optionally open the system browser (`wx.LaunchDefaultBrowser()`).
3. Wait for Pi to emit an auth-success or auth-failure event.

wxPi should **not** embed a webview for OAuth. System browser round-trips are simpler, safer, and
more accessible.

### 3.3 First-Run Flow

On first launch, if Pi has no configured providers, wxPi should present a guided provider setup
dialog that invokes `pi /login` as a subprocess and guides the user through it. This is the one
case where wxPi may need to capture Pi's interactive output rather than pure RPC events.

### 3.4 API Key Storage

If the user wants direct API keys (not OAuth), wxPi can provide a preferences dialog that writes
to Pi's `models.json` or environment variables. Never store keys in wxPi's own config.

---

## 4. Session / Thread Model

### 4.1 Pi Session Architecture

Pi sessions are JSONL files in `~/.pi/agent/sessions/`, keyed by working directory. Each entry has
an `id` and `parentId` forming a tree. Branching is supported; the entire tree lives in one file.

### 4.2 wxPi Session Abstractions

wxPi exposes sessions as a list in a side panel (like a browser history or conversation list).
Each session item shows: working directory, last message timestamp, message count.

**Key session operations wxPi must support:**
- `new session` — spawn fresh Pi process with empty session.
- `continue session` — spawn Pi with `--session <path>` and `--continue`.
- `fork session` — send RPC `fork` command; Pi creates branch at current point.
- `switch branch` — send RPC to navigate the session tree.
- `compact session` — send RPC `compact` to summarize old context.

### 4.3 Multi-Session UI Pattern

wxPi uses a **tab model** or a **session list + single panel** pattern. Tabs are familiar but
tricky for accessibility. Recommended: a session list in an `wx.SplitterWindow` left pane, with
the active session transcript on the right. Each session maps to exactly one Pi subprocess.

### 4.4 Thread Safety

Pi subprocess I/O runs on a background daemon thread. All wxPython UI updates must be dispatched
via `wx.CallAfter()` or `wx.PostEvent()`. The RPC bridge is a thread boundary — never touch wx
widgets from the reader thread.

---

## 5. Tool Call / Approval UX Mapping into wx

### 5.1 Tool Call Event Flow

```
Pi: tool_execution_start  → wxPi: render tool call block in transcript (read-only)
Pi: tool_execution_update → wxPi: update streaming output within tool block
Pi: tool_execution_end    → wxPi: finalize tool block, show result/error
```

For approval-required tools, Pi sends a `confirm` RPC request **before** `tool_execution_start`
and blocks. wxPi must respond before Pi proceeds.

### 5.2 Approval Dialog Design

When Pi sends a `confirm` UI request for a tool call:
1. wxPi raises a `wx.Dialog` with:
   - Tool name (e.g., `bash`).
   - Command/arguments (syntax-highlighted text or plain mono-spaced).
   - Working directory context.
   - Allow / Deny / Allow All Session buttons.
2. Dialog must be keyboard-navigable. Default focus: Deny (safe default).
3. Screen reader must announce the dialog open and the tool details before the buttons.
4. If user denies: send `{ "type": "confirm_response", "id": "...", "result": false }`.
5. If user allows: send `{ "type": "confirm_response", "id": "...", "result": true }`.

### 5.3 Tool Block Rendering in Transcript

The transcript is a `wx.html2.WebView` (or custom-painted `wx.Panel`) rendering a running log.
Tool blocks are visually distinct: collapsible, labeled with tool name, show streaming output.
When collapsed, screen reader should read the summary (tool name + status). When expanded, full
output is available.

Do NOT use `wx.TextCtrl` for the transcript — it cannot handle rich rendering, collapsible
sections, or efficient streaming updates.

### 5.4 "Allow All Session" Semantic

Pi does not have native "allow all session" for a tool type. wxPi implements this in the bridge:
maintain a per-session allow-list; auto-respond `true` to future `confirm` requests matching
that tool name/pattern without showing a dialog. This must be surfaced in a preference panel
and clearable.

---

## 6. Accessibility Architecture

This is the most architecturally significant section. Accessibility is a first-class requirement.

### 6.1 Screen Reader Support

**Platform targets:**
- Windows: NVDA + JAWS (via WinRT/MSAA/UIA). wxPython on Windows exposes native UIA.
- macOS: VoiceOver (via NSAccessibility). wxPython's Cocoa backend exposes native accessibility.
- Linux: Orca + AT-SPI2. wxPython/GTK backend exposes AT-SPI.

**Key principle:** Do not build custom accessibility. Use native wx widgets with correct roles,
names, and states. The transcript rendering choice is critical here (see 6.3).

### 6.2 Keyboard Navigation

All functionality must be reachable without a mouse:

| Action                  | Binding (default)       |
|-------------------------|-------------------------|
| Focus input field        | Ctrl+L or F6            |
| Submit prompt            | Enter (in input)        |
| New line in input        | Shift+Enter             |
| Abort current turn       | Escape or Ctrl+C        |
| Approve tool call        | Enter (in dialog)       |
| Deny tool call           | Escape (in dialog)      |
| Navigate session list    | Up/Down arrows          |
| Open session             | Enter                   |
| New session              | Ctrl+N                  |
| Continue/fork session    | Ctrl+F                  |
| Compact session          | Ctrl+Shift+K            |
| Toggle tool block expand | Space (in transcript)   |
| Copy transcript excerpt  | Ctrl+C (in transcript)  |
| Open preferences         | Ctrl+, or Alt+P         |

All bindings must be user-configurable. Avoid conflicts with system screen reader bindings
(NVDA uses Insert as modifier; JAWS uses Insert and Caps Lock).

### 6.3 Transcript Rendering — The Hard Decision

Three options:

**Option A: `wx.html2.WebView` with accessible HTML**
- Pro: Rich rendering (markdown, syntax highlighting), good browser accessibility model.
- Con: Chromium embed (large binary), AT-SPI bridging on Linux is imperfect, cross-platform focus
  management headaches, requires wx 4.2+.
- Con: Live region behavior for streaming requires JS injection; reliability varies.

**Option B: Custom-painted `wx.Panel` with virtual list**
- Pro: Full control, lightweight, can implement virtual scrolling for large transcripts.
- Con: Must implement accessibility from scratch using `wx.Accessible`, very time-intensive.
- Con: High risk of screen reader incompatibility. Not recommended for MVP.

**Option C: `wx.TextCtrl` (read-only, rich text) + separate tool block area**
- Pro: Native, free accessibility, works on all platforms.
- Con: Limited styling, no collapsible sections, hard to stream-append efficiently.
- Con: Emoji/Unicode rendering can be problematic.

**Option D: `wx.ListCtrl` (virtual list mode) for messages**
- Pro: Native widget, good screen reader support (each item is a row), virtual for large histories.
- Con: Each message is one row — nested structure (tool blocks inside messages) is awkward.

**Recommendation:** Start with **Option C** (rich `wx.TextCtrl`) for MVP — it gets screen reader
support for free. Migrate to **Option A** (WebView) in a later phase for richer rendering. The
migration path is clean: swap out the panel widget, keep the event/data layer unchanged.

### 6.4 Verbosity Modes

Implement a verbosity system with at least three levels:

- **Minimal**: User messages and final assistant responses only. No tool execution output.
- **Normal**: User + assistant + tool names and status (pass/fail). Tool output collapsed.
- **Verbose**: Everything, including streaming tool output.

Verbosity setting persists per-user. Screen reader users often prefer Minimal or Normal; sighted
users might prefer Verbose. This maps to what is rendered in the transcript AND what is announced
via `wx.Accessible` live-region equivalents.

### 6.5 Focus Management

Critical focus rules:
1. When a new assistant message starts streaming: do NOT steal focus from the input field.
   Update the transcript silently. Only announce "response received" when the turn ends.
2. When a tool approval dialog appears: steal focus to the dialog. Deny button has default focus.
3. When a turn ends: optionally move focus to the last assistant message (user-configurable).
4. When a session is loaded: focus goes to the input field.
5. On error: focus goes to the error panel/notification.

### 6.6 Live Announcements

wxPython does not have a built-in `aria-live` equivalent. Implement platform-specific live
announcement:

- **Windows**: Use `NotifyWinEvent` or a hidden `wx.TextCtrl` with UIA `LiveSetting` property
  set to `Assertive` for critical events (tool approval needed, error) and `Polite` for
  status updates (turn started, turn ended).
- **macOS**: Use `NSAccessibilityPostNotification` with `NSAccessibilityAnnouncementRequested`.
- **Linux**: Use AT-SPI2 `text-changed` events on a hidden panel or `atspi.generate_accessible_event`.

Abstract this behind an `Announcer` class with `announce(text, priority)` API. This is one of
the trickiest cross-platform pieces.

### 6.7 High Contrast / Theming

Support system high-contrast mode detection:
- Windows: `wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)` + check high-contrast system metric.
- macOS: `NSWorkspace.sharedWorkspace.accessibilityDisplayShouldIncreaseContrast`.
- Linux: GTK theme detection.

Never hard-code colors. Use `wx.SystemSettings` colors as base palette. Provide a preferences
option for explicit high-contrast override.

### 6.8 Font Scaling / DPI

Use `wx.Font` with point sizes. Respect system DPI scaling. Provide a font size preference in the
preferences dialog that scales the entire transcript and input area.

---

## 7. File / Workspace Handling

### 7.1 Working Directory

Pi sessions are scoped to a working directory. wxPi must surface this prominently:
- Title bar shows active working directory.
- A "Change Workspace" button/menu item (`Ctrl+Shift+O`) opens a `wx.DirDialog`.
- Spawns a new Pi process with the new CWD.

### 7.2 File References in Transcript

When Pi outputs file paths (in tool calls or assistant text), wxPi should:
- Detect path patterns using regex.
- Render them as clickable/activatable links in the transcript.
- On activation: open with system default application (`wx.LaunchDefaultApplication`) or reveal
  in file manager.
- Screen reader: announce as "link: <filename>" for navigability.

### 7.3 Drag and Drop

Accept files dragged onto the input area or transcript. On drop:
- For text files: offer to insert path into prompt or read content into prompt.
- For images: encode as base64 and include in the next `prompt` RPC call (Pi RPC supports images).

### 7.4 Workspace Profiles

Consider (later phase) a "workspaces" feature: named working directories with associated session
history, bookmarkable from the UI. Not MVP.

---

## 8. Error / Retry / Offline Behavior

### 8.1 Pi Process Crashes

The RPC bridge monitors the Pi subprocess. On unexpected exit:
1. Mark session as disconnected.
2. Show a non-blocking notification bar (not a modal — accessibility: modals are disruptive).
3. Offer "Reconnect" which re-spawns Pi with `--continue` on the same session file.
4. If reconnect fails: offer "Start New Session" as fallback.

### 8.2 RPC Timeout

Set a configurable timeout (default 30s) for Pi to respond to a `prompt` command with at least
one event. On timeout:
1. Send `abort` to Pi stdin.
2. Display timeout error in transcript.
3. Leave Pi process alive; allow user to retry.

### 8.3 API/Provider Errors

Pi emits provider errors as RPC events. wxPi renders them in the transcript as styled error
blocks with the error message and a suggested action (check API key, retry, switch model).

### 8.4 Offline / No Provider Configured

On startup, if Pi has no configured providers (RPC `get_models` returns empty), wxPi shows a
first-run setup wizard instead of the normal UI. This is not a blocking modal — it's the default
view, dismissable once setup completes.

### 8.5 Retry UX

Provide a "Retry Last Prompt" button/binding (`Ctrl+R`) that resends the last user message.
This uses `prompt` RPC with the same text. Implement at the wxPi layer; do not rely on Pi's
session tree for this.

---

## 9. Windows / macOS / Linux Platform Concerns

### 9.1 Process Spawning

- **Windows**: Use `subprocess.Popen` with `creationflags=subprocess.CREATE_NO_WINDOW` to
  suppress the console window for the Pi subprocess. PATH may not include `npm`-installed
  binaries — document that `pi` must be on system PATH or provide a path preference.
- **macOS**: Node.js may not be on PATH when launching from .app bundle (Dock vs. Terminal
  launch differences). Use `login -f -l $USER $SHELL -l -c "which pi"` or store the Pi
  binary path in preferences.
- **Linux**: Generally fine. Ensure Pi is on PATH or configurable.

### 9.2 Distribution

- **Windows**: Package with PyInstaller or cx_Freeze + bundle Node.js + pi binary, or require
  user to install Pi separately. The former is a huge binary but seamless; the latter requires
  technical users.
- **macOS**: `.app` bundle via `py2app`. Same Node.js bundling decision. Notarization required
  for distribution outside MAS.
- **Linux**: AppImage or flatpak (preferred for accessibility with AT-SPI2 bridge availability).
  `.deb`/`.rpm` for distro-specific packaging.

**Recommendation for MVP:** require Pi installed separately on system PATH. Document setup.
Bundling Node.js is a later-phase concern.

### 9.3 wxPython Backend Quirks

- **Windows** (`wx.MSW`): Best UIA/accessibility support. WxPython is mature here.
- **macOS** (`wx.OSX-Cocoa`): VoiceOver support is reasonable but `wx.html2.WebView` uses WKWebView
  and has known accessibility limitations. Test with VoiceOver on every release.
- **Linux** (`wx.GTK`): AT-SPI2 bridge is required. Works well with Orca+GTK. `wx.html2.WebView`
  uses WebKitGTK which has better AT-SPI support than Chromium on Linux.

### 9.4 High-DPI Displays

wxPython 4.2+ has improved DPI handling. Use `wx.App.EnableHighDPISupport()` on Windows.
Test on 4K displays and macOS Retina. Custom-painted widgets must scale correctly.

---

## 10. Security and Privacy Concerns

### 10.1 Pi's Security Model

Pi extensions run with full system permissions. wxPi does not use Pi extensions in the default
configuration, but if it supports user-installed extensions (later phase), it must surface the
same security warning Pi does.

### 10.2 Credential Safety

- wxPi never touches credentials directly. Credentials live in Pi's `~/.pi/` directory.
- The RPC channel is local-only (stdin/stdout of subprocess). No network exposure.
- If a preferences dialog writes to Pi config files, validate inputs to avoid path injection.

### 10.3 Tool Approval as Security Gate

The tool approval dialog is a critical security surface. Rules:
- Never auto-approve `bash` commands that include `rm`, `curl | sh`, or other high-risk patterns
  without explicit user action per command. The "Allow All Session" feature must exclude `bash`
  by default.
- Log all tool executions (with timestamps and results) to a local audit log in
  `~/.wxpi/sessions/<session_id>/audit.log`. This is separate from Pi's session JSONL.

### 10.4 No Telemetry Default

wxPi must not phone home by default. If analytics are added later, they must be opt-in, clearly
disclosed, and include no conversation content.

### 10.5 Session File Privacy

Pi session files contain full conversation history in plaintext JSONL. Document this clearly.
Consider (later phase) an encrypted session store — but this requires changes at the Pi layer
or a wrapper. Not MVP.

---

## 11. MVP vs. Later Phases

### 11.1 MVP (Phase 1): Core Viable Shell

**Goal:** A usable, accessible wxPython wrapper that a technical user can replace their Pi
terminal session with.

**Includes:**
- Single-session window: input field + transcript + status bar.
- RPC bridge: subprocess spawn, JSONL reader thread, event dispatch via `wx.CallAfter`.
- Transcript: `wx.TextCtrl` (rich, read-only), streaming append.
- Tool call blocks: inline text rendering with [TOOL: name | STATUS] markers.
- Tool approval dialog: confirm/deny, keyboard accessible.
- Basic keyboard navigation (all bindings in §6.2).
- Session open/continue/new from menu.
- Working directory selection.
- Provider not configured → setup instructions screen.
- Screen reader tested on one platform (recommend Windows + NVDA for MVP; broadest user base).
- Windows packaging: PyInstaller single-exe (Pi installed separately).

**Explicitly NOT in MVP:**
- Multi-session tabs.
- Rich HTML transcript rendering.
- File drag and drop.
- Verbosity modes.
- High-contrast auto-detection.
- Workspace profiles.
- Audit logging.
- macOS/Linux packaging.

### 11.2 Phase 2: Accessibility Hardening + Multi-Platform

- Full accessibility audit on all three platforms (NVDA, VoiceOver, Orca).
- Announcer class with platform-specific live region implementation.
- High-contrast mode detection and theming.
- Verbosity modes (Minimal/Normal/Verbose).
- Focus management polish (configurable post-turn focus behavior).
- macOS `.app` packaging + basic notarization.
- Linux AppImage packaging.
- Session list panel (splitter layout).
- Session fork and compact operations.

### 11.3 Phase 3: Rich UI + Power Features

- `wx.html2.WebView` transcript with accessible HTML, markdown rendering, syntax highlighting.
- File drag and drop.
- Workspace profiles.
- Image attachment in prompts.
- "Allow All Session" per-tool allow-list with management UI.
- Audit log viewer.
- Encrypted session store (pending Pi-layer support or wrapper).
- Model switching UI (leverages Pi's `get_models` RPC and model switch command).
- Session export (HTML export via Pi's `/export` equivalent in RPC).
- Pi package/extension management UI (later — security-sensitive).

---

## 12. Truly Hard Parts (Flagged)

These are the areas where the architecture is most likely to encounter unexpected complexity:

1. **Platform-specific live announcements (§6.6)**: wxPython has no `aria-live` equivalent.
   Implementing per-platform announcement is the single most fragile cross-platform piece.
   Budget significant research and testing time here.

2. **`wx.html2.WebView` accessibility on Linux (§6.3, §9.3)**: WebKitGTK's AT-SPI support is
   inconsistent across distro/webkit versions. The MVP `wx.TextCtrl` approach sidesteps this,
   but Phase 3's WebView migration will require careful AT-SPI testing.

3. **macOS PATH for Node.js subprocess (§9.1)**: GUI app launch on macOS does not inherit the
   user's shell PATH. The Pi binary (a global npm install) may not be findable. This is a known
   pain point for any native app wrapping a CLI tool. Requires a "locate Pi binary" setup step.

4. **Unicode line-split correctness in JSONL reader (§2.3)**: The Pi RPC docs explicitly warn
   against readers that split on Unicode paragraph/line separators. Python's `readline()` on
   `subprocess.stdout` (binary mode) is safe, but any layer that decodes to str before splitting
   (e.g., `io.TextIOWrapper`) may use a Unicode-aware splitter. Must be tested with payloads
   containing U+2028/U+2029.

5. **Session tree navigation UX**: Pi's session model is a tree, not a linear list. Presenting
   this intuitively (and accessibly) in a wx panel is non-trivial. A flat "most recent branches"
   list covers 90% of cases for MVP.

6. **Streaming performance for long sessions**: `wx.TextCtrl` append is O(n) for very long
   transcripts on some platforms. Will degrade for multi-hour coding sessions. Virtual list
   (Phase 3) is the fix; MVP should set a practical transcript truncation limit with a
   "scroll to load earlier" mechanism.

---

## 13. Recommendation: Should Josh Build on Pi?

See dedicated `RECOMMENDATION.md`.

---

## 14. Implementation Plan

See dedicated `IMPLEMENTATION.md`.
