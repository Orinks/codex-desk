# wxPi: Implementation Plan

**Status:** Active — v0.1 target
**Audience:** Josh (implementer)
**Last updated:** March 2026

This document is execution-oriented. It answers: what do I build, in what order, and what does
the file layout look like? For architectural rationale, see `ARCHITECTURE.md`.

---

## Milestones

### M1 — RPC Spike (1–2 days)

Prove that Python can drive Pi over JSONL before writing any wx code.

**Deliverable:** `spike/spike_rpc.py` — standalone script, not part of the `wxpi` package.

**Acceptance:** Script drives a Pi session end-to-end; streaming `message_update` deltas print
to console; U+2028/U+2029 in prompt payload does not corrupt the reader.

---

### M2 — PiBridge Module (2–3 days)

Production-grade bridge; fully unit-testable without live Pi.

**Deliverables:**
- `wxpi/rpc_bridge.py`
- `wxpi/rpc_events.py`
- `tests/fake_pi.py`
- `tests/test_rpc_bridge.py`

**Acceptance:** `pytest tests/` green; no live Pi needed; all PiBridge methods exercised.

---

### M3 — Minimal wx Shell (3–4 days)

Working window. User can prompt Pi and see responses.

**Deliverables:**
- `wxpi/app.py`
- `wxpi/main_frame.py`
- `wxpi/session_controller.py`
- Manual test: prompt → streaming response → tool block markers, no mouse required.

**Acceptance:** Full round-trip: type prompt, watch streaming response, see tool block appear,
Escape sends abort. All interactive widgets have `SetName()` applied.

---

### M4 — Tool Approval Dialog (2 days)

Approval flow complete and NVDA-verified.

**Deliverables:**
- `wxpi/approval_dialog.py`
- Integration in `session_controller.py`

**Acceptance:** ARCH §19 criteria A3–A6 pass with NVDA on Windows.

---

### M5 — Session Management + First-Run (2 days)

User can open, start, and switch sessions without restarting wxPi.

**Deliverables:**
- File menu: New Session, Open Session, Change Workspace
- `wxpi/first_run_panel.py`
- PyInstaller build check

**Acceptance:** User can open existing session, start new session, change workspace directory
— all from keyboard.

---

### M6 — Accessibility Pass + Windows Packaging (3–4 days)

All §19 criteria pass. Windows binary ships.

**Deliverables:**
- `build/windows/wxpi.spec` (PyInstaller)
- `ACCESSIBILITY_NOTES.md` (test results and known issues)
- Startup PATH check with friendly error dialog if `pi` not found

**Acceptance:** All 12 criteria in ARCH §19 pass on Windows + NVDA. A fresh-install tester
can follow README, install Pi, install wxPi, and complete a session.

---

## File / Module Structure

```
wxpi-arch/                         ← rename this repo (see ARCH §21 for name options)
│
├── wxpi/                          ← main package
│   ├── __init__.py
│   ├── app.py                     ← wx.App subclass; startup; PATH check
│   ├── main_frame.py              ← wx.Frame; layout; menu bar; status bar
│   ├── session_controller.py      ← owns PiBridge; wires events → UI via wx.CallAfter
│   ├── rpc_bridge.py              ← PiBridge class; subprocess; JSONL reader thread
│   ├── rpc_events.py              ← typed dataclasses for each Pi RPC event type
│   ├── approval_dialog.py         ← ToolApprovalDialog; allow-list store
│   ├── first_run_panel.py         ← shown when Pi not found / not configured
│   └── constants.py               ← key bindings, UI strings, config defaults
│
├── tests/
│   ├── fake_pi.py                 ← minimal script that emits scripted RPC event sequences
│   ├── test_rpc_bridge.py         ← unit tests for PiBridge (no live Pi)
│   └── test_approval_dialog.py    ← unit tests for allow-list logic (no wx needed)
│
├── spike/
│   └── spike_rpc.py               ← throwaway spike; kept for reference
│
├── build/
│   └── windows/
│       └── wxpi.spec              ← PyInstaller spec
│
├── ARCHITECTURE.md
├── IMPLEMENTATION_PLAN.md         ← this file
├── IMPLEMENTATION.md              ← original milestone writeup (supplementary)
├── RECOMMENDATION.md
├── README.md
├── requirements.txt               ← wxPython, (no other runtime deps for v0.1)
└── ACCESSIBILITY_NOTES.md         ← created during M6; platform test results
```

### Module responsibilities in one line each

| Module | Owns |
|--------|------|
| `app.py` | `wx.App` subclass; `OnInit()`; Pi PATH check; launch `MainFrame` |
| `main_frame.py` | `wx.Frame`; sizer layout; menu bar; status bar; routes key events to `SessionController` |
| `session_controller.py` | `PiBridge` lifecycle; event dispatch to UI; raises `ToolApprovalDialog`; allow-list |
| `rpc_bridge.py` | Subprocess spawn; background reader thread; JSONL write; callback registry |
| `rpc_events.py` | Dataclasses: `AgentStartEvent`, `MessageUpdateEvent`, `ConfirmEvent`, etc. |
| `approval_dialog.py` | `ToolApprovalDialog(wx.Dialog)`; `AllowList` class |
| `first_run_panel.py` | `FirstRunPanel(wx.Panel)`; retry logic; browser launch |
| `constants.py` | `DEFAULT_KEYBINDINGS`, `MAX_TRANSCRIPT_LINES`, `PI_BINARY_NAME` |

---

## First Coding Tasks

These are the first concrete things to write. Do them in order.

### Task 1 — Create the repo and skeleton

```bash
mkdir -p wxpi/wxpi wxpi/tests wxpi/spike wxpi/build/windows
touch wxpi/wxpi/__init__.py
touch wxpi/wxpi/constants.py
touch wxpi/requirements.txt
echo "wxPython>=4.2.0" > wxpi/requirements.txt
```

`constants.py` minimal start:

```python
PI_BINARY = "pi"
MAX_TRANSCRIPT_LINES = 5000
APP_NAME = "wxPi"
```

---

### Task 2 — Write `spike_rpc.py`

```python
# spike/spike_rpc.py
import subprocess, json, sys

proc = subprocess.Popen(
    ["pi", "--mode", "rpc"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

cmd = {"type": "prompt", "content": "list the files in the current directory"}
proc.stdin.write(json.dumps(cmd).encode() + b"\n")
proc.stdin.flush()

while True:
    line = proc.stdout.readline()   # byte-level; safe for U+2028/U+2029
    if not line:
        break
    event = json.loads(line.decode("utf-8"))
    print(event)
    if event.get("type") == "agent_end":
        break

proc.terminate()
```

Run it. If you see `agent_start` followed by `message_update` deltas, the spike passes.

---

### Task 3 — Write `rpc_events.py`

Define one dataclass per event type. Minimal first pass:

```python
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class AgentStartEvent:
    type: str = "agent_start"
    model: str = ""
    session_id: str = ""

@dataclass
class MessageUpdateEvent:
    type: str = "message_update"
    delta: str = ""

@dataclass
class ToolExecutionStartEvent:
    type: str = "tool_execution_start"
    tool: str = ""
    args: Any = None
    request_id: str = ""

@dataclass
class ToolExecutionEndEvent:
    type: str = "tool_execution_end"
    status: str = ""   # "success" | "error"
    exit_code: Optional[int] = None

@dataclass
class ConfirmEvent:
    type: str = "confirm"
    id: str = ""
    tool: str = ""
    args: Any = None
    cwd: str = ""

@dataclass
class AgentEndEvent:
    type: str = "agent_end"

# Add remaining types as they appear during M1 spike work.
```

---

### Task 4 — Write `rpc_bridge.py` skeleton

```python
import subprocess, json, threading
from typing import Callable, Optional

class PiBridge:
    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._callbacks: list[Callable] = []
        self._exit_callbacks: list[Callable] = []

    def start(self, cwd: str, session_path: Optional[str] = None,
              continue_session: bool = False) -> None:
        args = ["pi", "--mode", "rpc"]
        if session_path:
            args += ["--session", session_path]
        if continue_session:
            args += ["--continue"]
        self._proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
        )
        self._thread = threading.Thread(
            target=self._read_loop, daemon=True, name="pi-reader"
        )
        self._thread.start()

    def send_prompt(self, text: str) -> None:
        self._write({"type": "prompt", "content": text})

    def send_abort(self) -> None:
        self._write({"type": "abort"})

    def send_ui_response(self, request_id: str, result) -> None:
        self._write({"type": "confirm_response", "id": request_id, "result": result})

    def on_event(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def on_process_exit(self, callback: Callable) -> None:
        self._exit_callbacks.append(callback)

    def _write(self, obj: dict) -> None:
        if self._proc and self._proc.stdin:
            line = json.dumps(obj).encode("utf-8") + b"\n"
            self._proc.stdin.write(line)
            self._proc.stdin.flush()

    def _read_loop(self) -> None:
        assert self._proc and self._proc.stdout
        while True:
            raw = self._proc.stdout.readline()  # byte-level split on 0x0A only
            if not raw:
                break
            try:
                event = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                continue
            for cb in self._callbacks:
                cb(event)
        for cb in self._exit_callbacks:
            cb()
```

---

### Task 5 — Write `fake_pi.py` and first test

`tests/fake_pi.py` — emits a scripted sequence when spawned:

```python
#!/usr/bin/env python3
# tests/fake_pi.py — used by test_rpc_bridge.py as a subprocess stand-in
import json, sys, time

def emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

# Wait for a prompt command from stdin
line = sys.stdin.readline()
cmd = json.loads(line)
assert cmd["type"] == "prompt"

emit({"type": "agent_start", "model": "test-model", "session_id": "s1"})
emit({"type": "turn_start", "turn_id": "t1"})
emit({"type": "message_update", "delta": "Hello "})
emit({"type": "message_update", "delta": "world"})
emit({"type": "turn_end", "turn_id": "t1"})
emit({"type": "agent_end"})
```

`tests/test_rpc_bridge.py` — first test:

```python
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wxpi.rpc_bridge import PiBridge

FAKE_PI = [sys.executable, os.path.join(os.path.dirname(__file__), "fake_pi.py")]

def test_happy_path(monkeypatch):
    events = []
    bridge = PiBridge()
    monkeypatch.setattr("wxpi.rpc_bridge.PI_BINARY_ARGS", FAKE_PI)
    bridge.on_event(events.append)
    bridge.start(cwd="/tmp")
    bridge.send_prompt("hello")
    time.sleep(0.5)  # give reader thread time to drain

    types = [e["type"] for e in events]
    assert "agent_start" in types
    assert "message_update" in types
    assert "agent_end" in types
```

(Adjust the monkeypatch once `rpc_bridge.py` exposes the binary name as a configurable.)

---

## Risk Notes (actionable)

1. **Pi binary not on PATH on Windows**: add a startup check in `app.py` that calls
   `shutil.which("pi")` and shows `FirstRunPanel` if None. Do this in M3.

2. **U+2028/U+2029 JSONL split**: add a dedicated test in `test_rpc_bridge.py` that sends
   a payload containing `\u2028` and `\u2029` through `fake_pi.py` — do this in M2.

3. **wx.TextCtrl streaming perf**: set `MAX_TRANSCRIPT_LINES = 5000` in `constants.py` from day
   one; truncate in `session_controller.py` before the problem appears in testing.

4. **ShowModal() blocks the wx main thread while approval dialog is open**: this is intentional
   and correct. Pi is also blocked. Do not attempt to make it async in v0.1 — that path requires
   message pumping and is a v0.2 concern.
