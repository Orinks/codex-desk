"""Tests for the Pi auth service.

Written FIRST (TDD) — implementation in codex_desk/auth_service.py must make these green.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codex_desk.auth_service import AuthService


class BlockingProcess:
    """Simple fake process that waits for an event before exiting."""

    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self._done = threading.Event()

    def wait(self, timeout: float | None = None) -> int:
        finished = self._done.wait(timeout)
        if not finished:
            raise TimeoutError("fake process timed out")
        return self.returncode

    def poll(self) -> int | None:
        if self._done.is_set():
            return self.returncode
        return None

    def terminate(self) -> None:
        self.returncode = -15
        self._done.set()

    def finish(self) -> None:
        self._done.set()


def test_probe_state_reports_pi_missing(tmp_path: Path) -> None:
    """Service reports pi_missing when the Pi binary is not available."""
    service = AuthService(which=lambda _: None, auth_path=tmp_path / "auth.json")

    state = service.probe_state()

    assert state.status == "pi_missing"
    assert state.pi_installed is False
    assert state.authenticated is False


def test_probe_state_reports_authenticated_when_tokens_exist(tmp_path: Path) -> None:
    """Non-empty tokens in auth.json count as authenticated."""
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(json.dumps({"tokens": {"anthropic": {"accessToken": "abc"}}}))
    service = AuthService(which=lambda _: "/usr/bin/pi", auth_path=auth_path)

    state = service.probe_state()

    assert state.status == "authenticated"
    assert state.pi_installed is True
    assert state.auth_file_present is True
    assert state.authenticated is True


def test_probe_state_reports_unauthenticated_without_tokens(tmp_path: Path) -> None:
    """Missing or empty auth content remains unauthenticated."""
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(json.dumps({"tokens": {}}))
    service = AuthService(which=lambda _: "/usr/bin/pi", auth_path=auth_path)

    state = service.probe_state()

    assert state.status == "unauthenticated"
    assert state.pi_installed is True
    assert state.auth_file_present is True
    assert state.authenticated is False


def test_launch_login_returns_immediately_and_completes_in_background(tmp_path: Path) -> None:
    """Launching login should not block waiting for the subprocess to finish."""
    process = BlockingProcess(returncode=0)
    popen_calls: list[tuple[tuple[str, ...], dict]] = []

    def fake_popen(args, **kwargs):
        popen_calls.append((tuple(args), kwargs))
        return process

    service = AuthService(
        which=lambda _: "/usr/bin/pi",
        auth_path=tmp_path / "auth.json",
        popen=fake_popen,
    )

    started = time.monotonic()
    launch = service.launch_login()
    elapsed = time.monotonic() - started

    assert launch.status == "launched"
    assert launch.handle is not None
    assert elapsed < 0.2
    assert launch.handle.poll() is None
    assert popen_calls[0][0] == tuple(launch.command)

    process.finish()
    result = launch.handle.wait(timeout=1.0)
    assert result.status == "success"
    assert result.returncode == 0


def test_launch_login_captures_failure_exit_information(tmp_path: Path) -> None:
    """Failed login exits are surfaced in structured form."""
    process = BlockingProcess(returncode=7)
    service = AuthService(
        which=lambda _: "/usr/bin/pi",
        auth_path=tmp_path / "auth.json",
        popen=lambda *args, **kwargs: process,
    )

    launch = service.launch_login(provider="anthropic")
    process.finish()
    result = launch.handle.wait(timeout=1.0)

    assert result.status == "failed"
    assert result.returncode == 7
    assert result.provider == "anthropic"
    assert result.command[-1] == "anthropic"


def test_launch_login_reports_pi_missing_without_starting_process(tmp_path: Path) -> None:
    """The service should not try to launch login if Pi is unavailable."""
    popen_called = False

    def fake_popen(*args, **kwargs):
        nonlocal popen_called
        popen_called = True
        raise AssertionError("popen should not be called")

    service = AuthService(
        which=lambda _: None,
        auth_path=tmp_path / "auth.json",
        popen=fake_popen,
    )

    launch = service.launch_login()

    assert launch.status == "pi_missing"
    assert launch.handle is None
    assert popen_called is False
