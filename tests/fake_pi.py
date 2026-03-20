#!/usr/bin/env python3
"""
Deterministic fake Pi subprocess for tests.

Waits for a single 'prompt' command on stdin, then emits a scripted
sequence of JSONL events to stdout, then exits.

Used by test_rpc_bridge.py as a subprocess stand-in — no live Pi needed.
"""
import json
import sys


def emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main() -> None:
    line = sys.stdin.readline()
    if not line:
        sys.exit(1)
    try:
        cmd = json.loads(line)
    except json.JSONDecodeError:
        sys.exit(1)

    if cmd.get("type") != "prompt":
        sys.exit(1)

    emit({"type": "agent_start", "model": "test-model", "session_id": "s1"})
    emit({"type": "turn_start", "turn_id": "t1"})
    emit({"type": "message_update", "delta": "Hello "})
    emit({"type": "message_update", "delta": "world"})
    emit({"type": "turn_end", "turn_id": "t1"})
    emit({"type": "agent_end"})


if __name__ == "__main__":
    main()
