from __future__ import annotations

import json

from wxpi.codex_models import DEFAULT_MODEL_CHOICES, load_model_choices


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


def test_load_model_choices_falls_back_when_cache_missing(tmp_path):
    assert load_model_choices(tmp_path / "missing.json") == list(DEFAULT_MODEL_CHOICES)
