#!/usr/bin/env python3
"""Deterministic Codex app-server stand-in for bridge tests."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def record(obj: dict) -> None:
    log_path = os.environ.get("WXAGENT_FAKE_CODEX_LOG")
    if not log_path:
        return
    with Path(log_path).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(obj) + "\n")


def read_message() -> dict:
    line = sys.stdin.readline()
    if not line:
        sys.exit(1)
    message = json.loads(line)
    record(message)
    return message


def main() -> None:
    initialize = read_message()
    if initialize.get("method") != "initialize":
        sys.exit(2)
    emit({"id": initialize["id"], "result": {"serverInfo": {"name": "fake-codex"}}})

    initialized = read_message()
    if initialized.get("method") != "initialized":
        sys.exit(3)

    thread_start = read_message()
    if thread_start.get("method") != "thread/start":
        sys.exit(4)
    emit({"id": thread_start["id"], "result": {"thread": {"id": "thr_test"}}})

    turn_start = read_message()
    if turn_start.get("method") != "turn/start":
        sys.exit(5)
    emit({"method": "turn/started", "params": {"turn": {"id": "turn_test"}}})
    emit(
        {
            "method": "item/completed",
            "params": {"item": {"type": "agent_message", "text": "Hello from Codex"}},
        }
    )
    emit({"method": "turn/completed", "params": {"turn": {"id": "turn_test"}}})


if __name__ == "__main__":
    main()
