from __future__ import annotations

import json

from wxpi.codex_models import (
    DEFAULT_MODEL_CHOICES,
    default_reasoning_effort_for_model,
    load_model_choices,
    load_model_catalog,
    reasoning_efforts_for_model,
)


def test_load_model_choices_reads_codex_models_cache(tmp_path):
    cache_path = tmp_path / "models_cache.json"
    cache_path.write_text(
        json.dumps(
            {
                "models": [
                    {"slug": "gpt-5.5", "display_name": "GPT-5.5"},
                    {"slug": "codex-auto-review", "display_name": "Codex Auto Review"},
                ]
            }
        ),
        encoding="utf-8",
    )

    assert load_model_choices(cache_path) == ["gpt-5.5", "codex-auto-review"]


def test_load_model_catalog_reads_reasoning_efforts(tmp_path):
    cache_path = tmp_path / "models_cache.json"
    cache_path.write_text(
        json.dumps(
            {
                "models": [
                    {
                        "slug": "gpt-5.5",
                        "default_reasoning_level": "medium",
                        "supported_reasoning_levels": [
                            {"effort": "low"},
                            {"effort": "medium"},
                            {"effort": "high"},
                            {"effort": "xhigh"},
                        ],
                    },
                    {
                        "slug": "gpt-5.1",
                        "default_reasoning_level": "minimal",
                        "supported_reasoning_levels": [
                            {"effort": "none"},
                            {"effort": "minimal"},
                            {"effort": "low"},
                        ],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    catalog = load_model_catalog(cache_path)

    assert catalog[0].reasoning_efforts == ("low", "medium", "high", "xhigh")
    assert catalog[0].default_reasoning_effort == "medium"
    assert reasoning_efforts_for_model("gpt-5.1", cache_path) == ("none", "minimal", "low")
    assert default_reasoning_effort_for_model("gpt-5.1", cache_path) == "minimal"


def test_load_model_choices_falls_back_when_cache_missing(tmp_path):
    assert load_model_choices(tmp_path / "missing.json") == list(DEFAULT_MODEL_CHOICES)


def test_fallback_reasoning_efforts_match_current_codex_models(tmp_path):
    assert reasoning_efforts_for_model("gpt-5.5", tmp_path / "missing.json") == (
        "low",
        "medium",
        "high",
        "xhigh",
    )
