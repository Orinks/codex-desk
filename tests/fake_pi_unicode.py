#!/usr/bin/env python3
"""Fake Pi that emits message deltas containing U+2028 and U+2029."""
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

    emit({"type": "agent_start", "model": "test-model", "session_id": "unicode-s1"})
    emit({"type": "message_update", "delta": "line1\u2028line2\u2029line3"})
    emit({"type": "agent_end"})


if __name__ == "__main__":
    main()
