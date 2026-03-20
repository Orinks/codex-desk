"""Auth service for Pi auth probing and login launch."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Protocol

from wxpi.constants import PI_BINARY


DEFAULT_AUTH_PATH = Path.home() / ".pi" / "agent" / "auth.json"


class LoginProcess(Protocol):
    """Minimal subprocess interface used by LoginHandle."""

    returncode: int | None

    def wait(self, timeout: float | None = None) -> int: ...

    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...


AuthStateStatus = Literal["pi_missing", "unauthenticated", "authenticated"]
LaunchStatus = Literal["pi_missing", "launch_failed", "launched"]
LoginResultStatus = Literal["success", "failed", "cancelled"]


@dataclass(frozen=True)
class AuthState:
    """Current Pi auth availability as seen by wxPi."""

    status: AuthStateStatus
    pi_installed: bool
    auth_file_present: bool
    authenticated: bool
    auth_path: Path


@dataclass(frozen=True)
class LoginResult:
    """Structured subprocess completion information for Pi login."""

    status: LoginResultStatus
    returncode: int | None
    command: tuple[str, ...]
    provider: str | None


@dataclass(frozen=True)
class LoginLaunch:
    """Outcome of attempting to start the login helper."""

    status: LaunchStatus
    command: tuple[str, ...]
    handle: "LoginHandle | None"
    error: str | None = None


class LoginHandle:
    """Tracks a running login subprocess without blocking the caller."""

    def __init__(
        self,
        process: LoginProcess,
        command: tuple[str, ...],
        provider: str | None,
    ) -> None:
        self._process = process
        self._command = command
        self._provider = provider
        self._done = threading.Event()
        self._result: LoginResult | None = None
        self._thread = threading.Thread(
            target=self._wait_for_process,
            daemon=True,
            name="pi-login-waiter",
        )
        self._thread.start()

    def poll(self) -> int | None:
        """Return the current subprocess return code if it has exited."""
        return self._process.poll()

    def wait(self, timeout: float | None = None) -> LoginResult:
        """Wait for the subprocess to finish and return the structured result."""
        finished = self._done.wait(timeout)
        if not finished:
            raise TimeoutError("Pi login subprocess did not finish in time")
        assert self._result is not None
        return self._result

    def cancel(self) -> None:
        """Terminate the subprocess and let the watcher classify the exit."""
        self._process.terminate()

    def _wait_for_process(self) -> None:
        returncode = self._process.wait()
        status: LoginResultStatus
        if returncode == 0:
            status = "success"
        elif returncode in (-15, -9):
            status = "cancelled"
        else:
            status = "failed"
        self._result = LoginResult(
            status=status,
            returncode=returncode,
            command=self._command,
            provider=self._provider,
        )
        self._done.set()


class AuthService:
    """App-facing seam for Pi auth state and login bootstrap."""

    def __init__(
        self,
        *,
        which: Callable[[str], str | None] = shutil.which,
        auth_path: Path = DEFAULT_AUTH_PATH,
        popen: Callable[..., LoginProcess] = subprocess.Popen,
    ) -> None:
        self._which = which
        self._auth_path = auth_path
        self._popen = popen

    def probe_state(self) -> AuthState:
        """Inspect whether Pi is installed and auth appears present."""
        pi_installed = self._which(PI_BINARY) is not None
        auth_file_present = self._auth_path.exists()
        authenticated = False

        if pi_installed and auth_file_present:
            authenticated = self._has_tokens(self._auth_path)

        if not pi_installed:
            status: AuthStateStatus = "pi_missing"
        elif authenticated:
            status = "authenticated"
        else:
            status = "unauthenticated"

        return AuthState(
            status=status,
            pi_installed=pi_installed,
            auth_file_present=auth_file_present,
            authenticated=authenticated,
            auth_path=self._auth_path,
        )

    def is_configured(self) -> bool:
        """Compatibility helper for existing startup checks."""
        return self.probe_state().status == "authenticated"

    def launch_login(self, provider: str | None = None) -> LoginLaunch:
        """Start Pi's dedicated login helper and return immediately."""
        if self._which(PI_BINARY) is None:
            return LoginLaunch(status="pi_missing", command=(), handle=None)

        command = self._build_login_command(provider)
        try:
            process = self._popen(
                list(command),
                shell=sys.platform == "win32",
            )
        except OSError as exc:
            return LoginLaunch(
                status="launch_failed",
                command=command,
                handle=None,
                error=str(exc),
            )

        return LoginLaunch(
            status="launched",
            command=command,
            handle=LoginHandle(process=process, command=command, provider=provider),
        )

    @staticmethod
    def _has_tokens(auth_path: Path) -> bool:
        try:
            auth_data = json.loads(auth_path.read_text())
        except (OSError, json.JSONDecodeError):
            return False

        tokens = auth_data.get("tokens")
        if isinstance(tokens, dict):
            return any(bool(value) for value in tokens.values())
        if isinstance(tokens, list):
            return any(bool(value) for value in tokens)
        return False

    @staticmethod
    def _build_login_command(provider: str | None) -> tuple[str, ...]:
        command = [PI_BINARY, "/login"]
        if provider:
            command.append(provider)
        return tuple(command)
