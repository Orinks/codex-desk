"""User preferences for wxAgent sessions and transcript rendering."""

from __future__ import annotations

from dataclasses import dataclass


PERSONALITIES = ("none", "friendly", "pragmatic")
REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh")
SANDBOX_MODES = ("read-only", "workspace-write", "danger-full-access")
APPROVAL_POLICIES = ("untrusted", "on-request", "never")
APPROVAL_REVIEWERS = ("user", "auto_review")
THREAD_MODES = ("local", "worktree")


@dataclass(frozen=True)
class TranscriptPreferences:
    """Controls how much Codex process detail appears in the transcript."""

    show_tool_calls: bool = False
    show_reasoning: bool = False
    show_diagnostics: bool = False
    show_file_summaries: bool = True


@dataclass(frozen=True)
class AppPreferences:
    """Settings shared by new wxAgent threads."""

    personality: str = "none"
    transcript: TranscriptPreferences = TranscriptPreferences()

    def __post_init__(self) -> None:
        if self.personality not in PERSONALITIES:
            raise ValueError(f"unknown personality: {self.personality}")


@dataclass(frozen=True)
class ThreadOptions:
    """Options used when starting a Codex thread."""

    model: str = "gpt-5.4"
    reasoning_effort: str = "medium"
    sandbox: str = "workspace-write"
    approval_policy: str = "on-request"
    approvals_reviewer: str = "user"
    mode: str = "local"
    base_branch: str | None = None

    def __post_init__(self) -> None:
        if self.reasoning_effort not in REASONING_EFFORTS:
            raise ValueError(f"unknown reasoning effort: {self.reasoning_effort}")
        if self.sandbox not in SANDBOX_MODES:
            raise ValueError(f"unknown sandbox mode: {self.sandbox}")
        if self.approval_policy not in APPROVAL_POLICIES:
            raise ValueError(f"unknown approval policy: {self.approval_policy}")
        if self.approvals_reviewer not in APPROVAL_REVIEWERS:
            raise ValueError(f"unknown approvals reviewer: {self.approvals_reviewer}")
        if self.mode not in THREAD_MODES:
            raise ValueError(f"unknown thread mode: {self.mode}")
