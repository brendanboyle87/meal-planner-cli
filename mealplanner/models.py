"""Core domain models for the meal planner."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional


DAY_NAMES = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]
MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"]


@dataclass(frozen=True)
class Ingredient:
    """A single grocery item required by a recipe."""

    item: str
    qty: float
    unit: str
    category: str

    @staticmethod
    def from_dict(data: dict) -> "Ingredient":
        return Ingredient(
            item=data["item"],
            qty=float(data.get("qty", 0)),
            unit=data.get("unit", ""),
            category=data.get("category", "uncategorized"),
        )

    def to_dict(self) -> dict:
        return {
            "item": self.item,
            "qty": self.qty,
            "unit": self.unit,
            "category": self.category,
        }


@dataclass(frozen=True)
class Recipe:
    """A prepared meal that can be slotted into the weekly plan."""

    id: str
    name: str
    meals: List[str]
    tags: List[str]
    prep_time_min: float
    cook_time_min: float
    servings_per_recipe: float
    yields_prep_item: List[str]
    uses_prep_item: List[str]
    ingredients: List[Ingredient]

    @property
    def total_time_min(self) -> float:
        return self.prep_time_min + self.cook_time_min

    @staticmethod
    def from_dict(data: dict) -> "Recipe":
        return Recipe(
            id=data["id"],
            name=data.get("name", ""),
            meals=list(data.get("meals", [])),
            tags=list(data.get("tags", [])),
            prep_time_min=float(data.get("prep_time_min", 0)),
            cook_time_min=float(data.get("cook_time_min", 0)),
            servings_per_recipe=float(data.get("servings_per_recipe", 1)),
            yields_prep_item=list(data.get("yields_prep_item", [])),
            uses_prep_item=list(data.get("uses_prep_item", [])),
            ingredients=[Ingredient.from_dict(item) for item in data.get("ingredients", [])],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "meals": list(self.meals),
            "tags": list(self.tags),
            "prep_time_min": self.prep_time_min,
            "cook_time_min": self.cook_time_min,
            "servings_per_recipe": self.servings_per_recipe,
            "yields_prep_item": list(self.yields_prep_item),
            "uses_prep_item": list(self.uses_prep_item),
            "ingredients": [ingredient.to_dict() for ingredient in self.ingredients],
        }


@dataclass
class WeekConfig:
    """Configuration describing the preferences for a planning week."""

    week_start_date: date
    people: int
    variability_window_weeks: int
    max_daily_cook_times: Dict[str, Dict[str, float]]
    skip_meals: Dict[str, List[str]]
    enable_meal_prep_sunday: bool
    meal_prep_max_minutes: Optional[int]
    preferred_prep_items: List[str]
    pantry: List[str]

    @staticmethod
    def from_dict(data: dict) -> "WeekConfig":
        week_start = datetime.fromisoformat(data["week_start_date"]).date()
        return WeekConfig(
            week_start_date=week_start,
            people=int(data.get("people", 1)),
            variability_window_weeks=int(data.get("variability_window_weeks", 0)),
            max_daily_cook_times={
                day: {meal: float(limit) for meal, limit in meals.items()}
                for day, meals in data.get("max_daily_cook_times", {}).items()
            },
            skip_meals={day: list(meals) for day, meals in data.get("skip_meals", {}).items()},
            enable_meal_prep_sunday=bool(data.get("enable_meal_prep_sunday", False)),
            meal_prep_max_minutes=data.get("meal_prep_max_minutes"),
            preferred_prep_items=list(data.get("preferred_prep_items", [])),
            pantry=[item.lower() for item in data.get("pantry", [])],
        )

    def to_dict(self) -> dict:
        return {
            "week_start_date": self.week_start_date.isoformat(),
            "people": self.people,
            "variability_window_weeks": self.variability_window_weeks,
            "max_daily_cook_times": {
                day: dict(meals) for day, meals in self.max_daily_cook_times.items()
            },
            "skip_meals": {day: list(meals) for day, meals in self.skip_meals.items()},
            "enable_meal_prep_sunday": self.enable_meal_prep_sunday,
            "meal_prep_max_minutes": self.meal_prep_max_minutes,
            "preferred_prep_items": list(self.preferred_prep_items),
            "pantry": list(self.pantry),
        }

    def day_date(self, day_name: str) -> date:
        index = DAY_NAMES.index(day_name)
        return self.week_start_date + timedelta(days=index)


@dataclass
class PlanMeal:
    day_name: str
    date: date
    meal_type: str
    recipe_id: Optional[str]
    recipe_name: Optional[str]
    total_time_min: Optional[float]


@dataclass
class PlanDay:
    day_name: str
    date: date
    meals: List[PlanMeal] = field(default_factory=list)


def ensure_day_name(day: str) -> str:
    if day not in DAY_NAMES:
        raise ValueError(f"Unknown day name: {day}")
    return day
