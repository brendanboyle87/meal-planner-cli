"""Utilities for tracking recipe usage across weeks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .models import WeekConfig

PlanHistory = Dict[str, List[str]]


class HistoryStore:
    """Persists and retrieves meal plan history data."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> Optional[PlanHistory]:
        if not self.path.exists():
            return None
        with self.path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        history = data.get("plans") if isinstance(data, dict) else data
        if isinstance(history, dict):
            return {str(week): list(recipes) for week, recipes in history.items()}
        if isinstance(history, list):
            result: PlanHistory = {}
            for entry in history:
                if not isinstance(entry, dict):
                    continue
                week = entry.get("week_start_date")
                recipes = entry.get("recipes", [])
                if isinstance(week, str) and isinstance(recipes, list):
                    result[week] = [str(recipe) for recipe in recipes]
            return result
        return None

    def record_plan(self, plan: dict, config: WeekConfig) -> None:
        history = self.load() or {}
        week_start = plan.get("week_start_date", config.week_start_date.isoformat())
        recipes: List[str] = []
        for day in plan.get("days", []):
            for meal in day.get("meals", []):
                recipe_id = meal.get("recipe_id")
                if recipe_id:
                    recipes.append(recipe_id)
        history[week_start] = recipes

        if config.variability_window_weeks > 0:
            weeks_to_keep = config.variability_window_weeks
            sorted_weeks = sorted(history.keys())
            if len(sorted_weeks) > weeks_to_keep:
                for week in sorted_weeks[:-weeks_to_keep]:
                    history.pop(week, None)

        payload = {"plans": history}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
