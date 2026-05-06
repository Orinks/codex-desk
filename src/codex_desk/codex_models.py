"""Codex model choice discovery."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
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
DEFAULT_REASONING_EFFORTS_BY_MODEL = {
    "gpt-5.5": ("low", "medium", "high", "xhigh"),
    "gpt-5.4": ("low", "medium", "high", "xhigh"),
    "gpt-5.4-mini": ("low", "medium", "high", "xhigh"),
    "gpt-5.3-codex": ("low", "medium", "high", "xhigh"),
    "gpt-5.3-codex-spark": ("low", "medium", "high", "xhigh"),
    "gpt-5.2": ("low", "medium", "high", "xhigh"),
    "codex-auto-review": ("low", "medium", "high", "xhigh"),
}
FALLBACK_REASONING_EFFORTS = ("low", "medium", "high", "xhigh")


@dataclass(frozen=True)
class CodexModelInfo:
    """Locally cached Codex model metadata needed by Codex Desk controls."""

    slug: str
    reasoning_efforts: tuple[str, ...] = FALLBACK_REASONING_EFFORTS
    default_reasoning_effort: str = "medium"


def default_models_cache_path() -> Path:
    """Return the Codex model cache path."""
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home) / "models_cache.json"
    return Path.home() / ".codex" / "models_cache.json"


def load_model_choices(cache_path: Path | None = None) -> list[str]:
    """Return selectable model slugs from Codex's local model cache."""
    return [model.slug for model in load_model_catalog(cache_path)]


def load_model_catalog(cache_path: Path | None = None) -> list[CodexModelInfo]:
    """Return model metadata from Codex's local model cache."""
    path = cache_path or default_models_cache_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default_model_catalog()

    models = data.get("models")
    if not isinstance(models, list):
        return _default_model_catalog()

    catalog = []
    seen = set()
    for model in models:
        if not isinstance(model, dict):
            continue
        slug = model.get("slug")
        if not isinstance(slug, str) or not slug or slug in seen:
            continue
        seen.add(slug)
        catalog.append(
            CodexModelInfo(
                slug=slug,
                reasoning_efforts=_parse_reasoning_efforts(model, slug),
                default_reasoning_effort=_parse_default_reasoning_effort(model, slug),
            )
        )
    return catalog or _default_model_catalog()


def reasoning_efforts_for_model(model: str, cache_path: Path | None = None) -> tuple[str, ...]:
    """Return reasoning efforts supported by a model."""
    for model_info in load_model_catalog(cache_path):
        if model_info.slug == model:
            return model_info.reasoning_efforts
    return DEFAULT_REASONING_EFFORTS_BY_MODEL.get(model, FALLBACK_REASONING_EFFORTS)


def default_reasoning_effort_for_model(model: str, cache_path: Path | None = None) -> str:
    """Return the model's default reasoning effort."""
    for model_info in load_model_catalog(cache_path):
        if model_info.slug == model:
            return model_info.default_reasoning_effort
    efforts = DEFAULT_REASONING_EFFORTS_BY_MODEL.get(model, FALLBACK_REASONING_EFFORTS)
    return "medium" if "medium" in efforts else efforts[0]


def _default_model_catalog() -> list[CodexModelInfo]:
    return [
        CodexModelInfo(
            slug=model,
            reasoning_efforts=DEFAULT_REASONING_EFFORTS_BY_MODEL.get(
                model, FALLBACK_REASONING_EFFORTS
            ),
            default_reasoning_effort="medium",
        )
        for model in DEFAULT_MODEL_CHOICES
    ]


def _parse_reasoning_efforts(model: dict, slug: str) -> tuple[str, ...]:
    levels = model.get("supported_reasoning_levels")
    if isinstance(levels, list):
        efforts = tuple(
            effort
            for level in levels
            if isinstance(level, dict)
            for effort in [level.get("effort")]
            if isinstance(effort, str) and effort
        )
        if efforts:
            return efforts
    return DEFAULT_REASONING_EFFORTS_BY_MODEL.get(slug, FALLBACK_REASONING_EFFORTS)


def _parse_default_reasoning_effort(model: dict, slug: str) -> str:
    default = model.get("default_reasoning_level")
    efforts = _parse_reasoning_efforts(model, slug)
    if isinstance(default, str) and default in efforts:
        return default
    return "medium" if "medium" in efforts else efforts[0]
