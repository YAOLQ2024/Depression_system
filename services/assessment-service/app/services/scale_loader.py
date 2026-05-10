from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.config import get_settings


@dataclass(frozen=True)
class ScaleOption:
    score: int
    label: str


@dataclass(frozen=True)
class ScaleItem:
    id: str
    index: int
    text: str


@dataclass(frozen=True)
class ScaleDefinition:
    slug: str
    code: str
    name: str
    short_name: str
    mode: str
    timeframe: str | None
    item_count: int
    answer_options: tuple[ScaleOption, ...]
    items: tuple[ScaleItem, ...]
    scoring: dict[str, Any]
    risk_flags: tuple[dict[str, Any], ...]
    source: dict[str, Any]
    notes: tuple[str, ...]

    def build_catalog_entry(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "code": self.code,
            "name": self.name,
            "short_name": self.short_name,
            "mode": self.mode,
            "timeframe": self.timeframe,
            "item_count": self.item_count,
            "answer_options": [{"score": option.score, "label": option.label} for option in self.answer_options],
        }


class ScaleLoaderError(Exception):
    pass


class ScaleLoader:
    def __init__(self, resource_root: Path, active_scale_slugs: list[str]):
        self._scale_dir = resource_root / "scales"
        self._active_scale_slugs = list(active_scale_slugs)

    @property
    def active_scale_slugs(self) -> list[str]:
        return list(self._active_scale_slugs)

    def load_scale(self, slug: str) -> ScaleDefinition:
        scale_path = self._scale_dir / f"{slug}.yaml"
        if not scale_path.exists():
            raise ScaleLoaderError(f"scale resource not found: {slug}")

        with scale_path.open("r", encoding="utf-8") as file:
            payload = yaml.safe_load(file) or {}

        metadata = payload.get("metadata") or {}
        items = payload.get("items") or []
        answer_options = payload.get("answer_options") or []
        notes = payload.get("notes") or payload.get("scoring", {}).get("notes") or []

        return ScaleDefinition(
            slug=metadata["slug"],
            code=metadata["code"],
            name=metadata["name"],
            short_name=metadata.get("short_name") or metadata["name"],
            mode=metadata.get("mode", "voice_self_report"),
            timeframe=metadata.get("timeframe"),
            item_count=int(metadata.get("item_count") or len(items)),
            answer_options=tuple(
                ScaleOption(score=int(option["score"]), label=str(option["label"]))
                for option in answer_options
            ),
            items=tuple(
                ScaleItem(id=str(item["id"]), index=int(item["index"]), text=str(item["text"]))
                for item in items
            ),
            scoring=dict(payload.get("scoring") or {}),
            risk_flags=tuple(dict(flag) for flag in (payload.get("risk_flags") or [])),
            source=dict(payload.get("source") or {}),
            notes=tuple(str(note) for note in notes),
        )

    def load_active_scales(self) -> list[ScaleDefinition]:
        return [self.load_scale(slug) for slug in self._active_scale_slugs]

    def build_catalog(self) -> list[dict[str, Any]]:
        return [scale.build_catalog_entry() for scale in self.load_active_scales()]


@lru_cache(maxsize=1)
def get_scale_loader() -> ScaleLoader:
    settings = get_settings()
    return ScaleLoader(
        resource_root=Path(settings["workflow_resources_dir"]),
        active_scale_slugs=list(settings["active_scale_slugs"]),
    )
