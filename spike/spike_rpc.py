#!/usr/bin/env python3
"""
M1 RPC spike — proves Python can drive Pi over JSONL.

Run from the repo root:
    python3 spike/spike_rpc.py

Acceptance:
- Prints agent_start, then message_update deltas, then agent_end.
- U+2028 / U+2029 in a prompt payload do not corrupt the JSONL reader.
- No wx, no wxpi package — standalone throwaway script.
"""
import json
import subprocess
import sys


def main() -> None:
    try:
        proc = subprocess.Popen(
            ["pi", "--mode", "rpc"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        print("ERROR: 'pi' binary not found on PATH.", file=sys.stderr)
        print("Install Pi and ensure it is accessible, then re-run.", file=sys.stderr)
        sys.exit(1)

    # U+2028 (LINE SEPARATOR) and U+2029 (PARAGRAPH SEPARATOR) are legal in
    # JSON strings but *must not* cause our reader to split the line early.
    # readline() on raw bytes splits only on 0x0A, so they are safe here.
    prompt = "list the files in the current directory\u2028\u2029"
    cmd = {"type": "prompt", "content": prompt}
    proc.stdin.write(json.dumps(cmd).encode("utf-8") + b"\n")
    proc.stdin.flush()

    while True:
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

    proc.terminate()


if __name__ == "__main__":
    main()
