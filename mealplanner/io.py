"""Utility functions for reading structured data from disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from .models import Recipe, WeekConfig


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_recipes(path: Path) -> List[Recipe]:
    data = _read_json(path)
    recipes: List[Recipe] = []
    for raw in data:
        recipes.append(Recipe.from_dict(raw))
    return recipes


def _load_pantry_from_file(pantry_path: Path) -> List[str]:
    if not pantry_path.exists():
        return []

    content = pantry_path.read_text(encoding="utf-8")
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = None

    if isinstance(data, list):
        return [str(item) for item in data if str(item).strip()]

    items: List[str] = []
    for line in content.splitlines():
        item = line.strip()
        if not item or item.startswith("#"):
            continue
        items.append(item)
    return items


def load_config(path: Path) -> WeekConfig:
    data = _read_json(path)

    pantry_items: List[str] = list(data.get("pantry", []))
    pantry_file = data.get("pantry_file")
    if pantry_file:
        pantry_path = Path(pantry_file)
        if not pantry_path.is_absolute():
            pantry_path = path.parent / pantry_path
        pantry_from_file = _load_pantry_from_file(pantry_path)
        pantry_items.extend(pantry_from_file)
    if pantry_items:
        # Preserve order while removing duplicates
        data["pantry"] = list(dict.fromkeys(pantry_items))
    else:
        data.setdefault("pantry", [])

    return WeekConfig.from_dict(data)


def load_plan_json(path: Path) -> dict:
    return _read_json(path)


def dump_recipes(path: Path, recipes: Iterable[Recipe]) -> None:
    data = [recipe.to_dict() for recipe in recipes]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
