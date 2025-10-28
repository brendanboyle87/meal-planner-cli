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


def load_config(path: Path) -> WeekConfig:
    data = _read_json(path)
    return WeekConfig.from_dict(data)


def load_plan_json(path: Path) -> dict:
    return _read_json(path)


def dump_recipes(path: Path, recipes: Iterable[Recipe]) -> None:
    data = [recipe.to_dict() for recipe in recipes]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
