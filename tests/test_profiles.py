from __future__ import annotations

import pytest

from wxpi.profiles import default_profile, get_profile, list_profiles


def test_default_profile_is_vanilla_codex():
    profile = default_profile()

    assert profile.id == "vanilla-codex"
    assert profile.installed_by_default is True
    assert profile.install_steps == ()


def test_optional_superpower_profiles_are_discoverable_but_not_auto_installed():
    profiles = {profile.id: profile for profile in list_profiles()}

    assert {"oh-my-codex", "obra", "compound-engineering"} <= set(profiles)
    assert all(not profiles[id].installed_by_default for id in profiles if id != "vanilla-codex")
    assert all(profiles[id].install_steps for id in profiles if id != "vanilla-codex")


def test_get_profile_rejects_unknown_id():
    with pytest.raises(KeyError):
        get_profile("not-real")
