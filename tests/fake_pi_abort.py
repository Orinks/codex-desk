#!/usr/bin/env python3
"""Fake Pi that emits a start event, then waits for an abort command."""
import json
import sys


def emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main() -> None:
    line = sys.stdin.readline()
    if not line:
        sys.exit(1)
    cmd = json.loads(line)
    if cmd.get("type") != "prompt":
        sys.exit(1)

    emit({"type": "agent_start", "model": "test-model", "session_id": "abort-s1"})

    line = sys.stdin.readline()
    if not line:
        sys.exit(1)
    cmd = json.loads(line)
    if cmd.get("type") != "abort":
        sys.exit(1)

    emit({"type": "agent_end", "status": "aborted"})


if __name__ == "__main__":
    main()
