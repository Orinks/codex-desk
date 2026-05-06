"""Installable capability profiles for Codex Desk."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentProfile:
    id: str
    name: str
    description: str
    installed_by_default: bool = False
    install_steps: tuple[str, ...] = ()


_PROFILES: tuple[AgentProfile, ...] = (
    AgentProfile(
        id="vanilla-codex",
        name="Vanilla Codex",
        description="Use the local Codex CLI/app-server with no extra workflow layer.",
        installed_by_default=True,
    ),
    AgentProfile(
        id="oh-my-codex",
        name="Oh My Codex",
        description="Add OMX workflow skills, agent roles, and local orchestration helpers.",
        install_steps=("Install or update oh-my-codex in the selected workspace.",),
    ),
    AgentProfile(
        id="obra",
        name="Obra",
        description="Install Obra-oriented workflow extensions when the user opts in.",
        install_steps=("Run the Obra installer once the upstream install contract is confirmed.",),
    ),
    AgentProfile(
        id="compound-engineering",
        name="Compound Engineering",
        description="Install Compound Engineering workflow extensions when the user opts in.",
        install_steps=(
            "Run the Compound Engineering installer once the upstream install contract is confirmed.",
        ),
    ),
)


def list_profiles() -> tuple[AgentProfile, ...]:
    return _PROFILES


def default_profile() -> AgentProfile:
    return _PROFILES[0]


def get_profile(profile_id: str) -> AgentProfile:
    for profile in _PROFILES:
        if profile.id == profile_id:
            return profile
    raise KeyError(profile_id)
