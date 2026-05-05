"""Codex model choice discovery."""

from __future__ import annotations

import json
import os
from pathlib import Path


DEFAULT_MODEL_CHOICES = (
    "gpt-5.5",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.3-codex",
    "gpt-5.3-codex-spark",
    "gpt-5.2",
    "codex-auto-review",
)


def default_models_cache_path() -> Path:
    """Return the Codex model cache path."""
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home) / "models_cache.json"
    return Path.home() / ".codex" / "models_cache.json"


def load_model_choices(cache_path: Path | None = None) -> list[str]:
    """Return selectable model slugs from Codex's local model cache."""
    path = cache_path or default_models_cache_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return list(DEFAULT_MODEL_CHOICES)

    models = data.get("models")
    if not isinstance(models, list):
        return list(DEFAULT_MODEL_CHOICES)

    choices = []
    for model in models:
        if not isinstance(model, dict):
            continue
        slug = model.get("slug")
        if isinstance(slug, str) and slug and slug not in choices:
            choices.append(slug)
    return choices or list(DEFAULT_MODEL_CHOICES)
