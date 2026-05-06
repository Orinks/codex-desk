#!/usr/bin/env python3
"""
M1/M2 RPC spike — proves Python can drive Pi over documented JSONL RPC.

Run from the repo root:
    python3 spike/spike_rpc.py

Acceptance:
- Prints a successful get_state response from the live Pi binary.
- Prints prompt acceptance plus streamed events until agent_end.
- U+2028 / U+2029 in a prompt payload do not corrupt the JSONL reader.
- No wx, no codex_desk package — standalone throwaway script.
"""
import json
import subprocess
import sys
import time


def send(proc: subprocess.Popen[bytes], obj: dict) -> None:
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(obj).encode("utf-8") + b"\n")
    proc.stdin.flush()


def main() -> None:
    try:
        proc = subprocess.Popen(
            ["pi", "--mode", "rpc", "--no-session"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        print("ERROR: 'pi' binary not found on PATH.", file=sys.stderr)
        print("Install Pi and ensure it is accessible, then re-run.", file=sys.stderr)
        sys.exit(1)

    # First prove the RPC command/response channel is alive.
    send(proc, {"id": "state-1", "type": "get_state"})

    # U+2028 (LINE SEPARATOR) and U+2029 (PARAGRAPH SEPARATOR) are legal in
    # JSON strings but *must not* cause our reader to split the line early.
    prompt = "Reply with exactly ok\u2028\u2029"
    send(proc, {"id": "prompt-1", "type": "prompt", "message": prompt})

    deadline = time.time() + 20
    while time.time() < deadline:
        raw = proc.stdout.readline()  # byte-level; splits on 0x0A only
        if not raw:
            break
        try:
            event = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            print(f"PARSE ERROR: {exc!r}", file=sys.stderr)
            continue
        print(event)
        if event.get("type") == "agent_end":
            break
    else:
        print("TIMEOUT waiting for agent_end", file=sys.stderr)

    proc.terminate()
    try:
        _, stderr = proc.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        _, stderr = proc.communicate()

    if stderr:
        print("STDERR:", file=sys.stderr)
        print(stderr.decode("utf-8", errors="replace"), file=sys.stderr)


if __name__ == "__main__":
    main()
