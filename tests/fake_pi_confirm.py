#!/usr/bin/env python3
"""Fake Pi that emits a confirm event and waits for a confirm_response."""
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

    emit({"type": "agent_start", "model": "test-model", "session_id": "confirm-s1"})
    emit(
        {
            "type": "confirm",
            "id": "req-1",
            "tool": "bash",
            "args": {"command": "echo hi"},
            "cwd": "/tmp",
        }
    )

    line = sys.stdin.readline()
    if not line:
        sys.exit(1)
    cmd = json.loads(line)
    if cmd.get("type") != "confirm_response" or cmd.get("id") != "req-1":
        sys.exit(1)

    emit({"type": "message_update", "delta": f"confirmed:{cmd.get('result')}"})
    emit({"type": "agent_end"})


if __name__ == "__main__":
    main()
