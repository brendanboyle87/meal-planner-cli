"""Logic responsible for building the weekly meal plan."""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Set

from .models import DAY_NAMES, MEAL_TYPES, PlanDay, PlanMeal, Recipe, WeekConfig


class PlanningError(RuntimeError):
    """Raised when the planner cannot find a valid schedule."""


PlanHistory = Dict[str, List[str]]


def _recipes_for_meal(recipes: Sequence[Recipe], meal: str) -> List[Recipe]:
    return [recipe for recipe in recipes if meal in recipe.meals]


def _filter_by_time_limit(
    recipes: Iterable[Recipe],
    limit_minutes: Optional[float],
) -> List[Recipe]:
    if limit_minutes is None:
        return list(recipes)
    return [recipe for recipe in recipes if recipe.total_time_min <= limit_minutes]


def _avoid_recent_recipes(
    recipes: Iterable[Recipe],
    forbidden: Set[str],
) -> List[Recipe]:
    remaining = [recipe for recipe in recipes if recipe.id not in forbidden]
    return remaining or list(recipes)


def _choose_recipe(
    recipes: Sequence[Recipe],
    rng: random.Random,
) -> Optional[Recipe]:
    if not recipes:
        return None
    return rng.choice(recipes)


def _gather_recent_history(
    history: Optional[PlanHistory],
    current_week: WeekConfig,
) -> Set[str]:
    if not history:
        return set()

    week_start = current_week.week_start_date
    window = current_week.variability_window_weeks
    forbidden: Set[str] = set()

    for entry_week, recipe_ids in history.items():
        try:
            entry_date = datetime.fromisoformat(entry_week).date()
        except ValueError:
            continue
        if window <= 0:
            forbidden.update(recipe_ids)
            continue
        delta_weeks = (week_start - entry_date).days // 7
        if 0 < delta_weeks <= window:
            forbidden.update(recipe_ids)
    return forbidden

def generate_plan(
    recipes: Sequence[Recipe],
    config: WeekConfig,
    history: Optional[PlanHistory],
    *,
    seed: Optional[int] = None,
) -> dict:
    """Generate a weekly plan as a serialisable dictionary."""

    rng = random.Random(seed)
    plan_days: List[PlanDay] = []
    recent_recipes = _gather_recent_history(history, config)
    recipe_lookup: Dict[str, Recipe] = {recipe.id: recipe for recipe in recipes}

    for day_name in DAY_NAMES:
        day_date = config.day_date(day_name)
        plan_day = PlanDay(day_name=day_name, date=day_date)
        plan_days.append(plan_day)

        skip_meals = set(meal.lower() for meal in config.skip_meals.get(day_name, []))
        cook_time_limits = {
            meal.lower(): limit for meal, limit in config.max_daily_cook_times.get(day_name, {}).items()
        }

        for meal in MEAL_TYPES:
            if meal in skip_meals:
                plan_day.meals.append(
                    PlanMeal(
                        day_name=day_name,
                        date=day_date,
                        meal_type=meal,
                        recipe_id=None,
                        recipe_name=None,
                        total_time_min=None,
                    )
                )
                continue

            candidates = _recipes_for_meal(recipes, meal)
            limit = cook_time_limits.get(meal)
            candidates = _filter_by_time_limit(candidates, limit)
            candidates = _avoid_recent_recipes(candidates, recent_recipes)

            recipe = _choose_recipe(candidates, rng)
            if recipe is None:
                plan_day.meals.append(
                    PlanMeal(
                        day_name=day_name,
                        date=day_date,
                        meal_type=meal,
                        recipe_id=None,
                        recipe_name=None,
                        total_time_min=None,
                    )
                )
                continue

            plan_day.meals.append(
                PlanMeal(
                    day_name=day_name,
                    date=day_date,
                    meal_type=meal,
                    recipe_id=recipe.id,
                    recipe_name=recipe.name,
                    total_time_min=recipe.total_time_min,
                )
            )

    plan_dict = {
        "week_start_date": config.week_start_date.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": seed,
        "days": [
            {
                "day_name": day.day_name,
                "date": day.date.isoformat(),
                "meals": [
                    {
                        "meal_type": meal.meal_type,
                        "recipe_id": meal.recipe_id,
                        "recipe_name": meal.recipe_name,
                        "total_time_min": meal.total_time_min,
                    }
                    for meal in day.meals
                ],
            }
            for day in plan_days
        ],
        "metadata": {
            "people": config.people,
            "variability_window_weeks": config.variability_window_weeks,
            "recent_recipes": sorted(recent_recipes),
        },
    }

    plan_dict["summary"] = _build_summary(plan_dict, recipe_lookup)
    return plan_dict


def _build_summary(plan: dict, recipe_lookup: Dict[str, Recipe]) -> dict:
    yield_map: Dict[str, List[str]] = defaultdict(list)
    for day in plan["days"]:
        for meal in day["meals"]:
            recipe_id = meal.get("recipe_id")
            if not recipe_id:
                continue
            recipe = recipe_lookup.get(recipe_id)
            if not recipe:
                continue
            for prep_item in recipe.yields_prep_item:
                yield_map[prep_item].append(recipe.name)

    return {
        "yielded_prep_items": yield_map,
    }
