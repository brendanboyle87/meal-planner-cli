"""Aggregate grocery items from a generated meal plan."""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from .models import Recipe, WeekConfig


class GroceryItem:
    """Represents a single aggregated grocery line item."""

    __slots__ = ("item", "quantity", "unit", "category", "sources")

    def __init__(self, item: str, quantity: float, unit: str, category: str) -> None:
        self.item = item
        self.quantity = quantity
        self.unit = unit
        self.category = category
        self.sources: List[str] = []

    def add_source(self, description: str) -> None:
        self.sources.append(description)

    def as_tuple(self) -> Tuple[str, float, str, str]:
        return (self.item, self.quantity, self.unit, self.category)


def _recipe_lookup(recipes: Iterable[Recipe]) -> Dict[str, Recipe]:
    return {recipe.id: recipe for recipe in recipes}


def _meal_description(day: dict, meal: dict) -> str:
    return f"{day['day_name']} {meal['meal_type'].title()}"


def collect_grocery_items(plan: dict, recipes: Iterable[Recipe], config: WeekConfig) -> List[GroceryItem]:
    lookup = _recipe_lookup(recipes)
    pantry = set(config.pantry)
    aggregated: Dict[Tuple[str, str], GroceryItem] = {}

    for day in plan.get("days", []):
        for meal in day.get("meals", []):
            recipe_id = meal.get("recipe_id")
            if not recipe_id:
                continue
            recipe = lookup.get(recipe_id)
            if not recipe:
                continue

            multiplier = config.people / recipe.servings_per_recipe if recipe.servings_per_recipe else 1.0
            source = _meal_description(day, meal)

            for ingredient in recipe.ingredients:
                item_key = ingredient.item.lower()
                if item_key in pantry:
                    continue
                key = (item_key, ingredient.unit)
                qty = ingredient.qty * multiplier
                if key not in aggregated:
                    aggregated[key] = GroceryItem(
                        item=ingredient.item,
                        quantity=0.0,
                        unit=ingredient.unit,
                        category=ingredient.category,
                    )
                aggregated[key].quantity += qty
                aggregated[key].add_source(source)

    return sorted(aggregated.values(), key=lambda item: (item.category, item.item))


def build_grocery_table(items: List[GroceryItem]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["item", "quantity", "unit", "category", "sources"])
    for item in items:
        writer.writerow(
            [
                item.item,
                f"{item.quantity:.2f}",
                item.unit,
                item.category,
                "; ".join(item.sources),
            ]
        )
    return buffer.getvalue()


def build_grocery_markdown(items: List[GroceryItem]) -> str:
    by_category: Dict[str, List[GroceryItem]] = defaultdict(list)
    for item in items:
        by_category[item.category].append(item)

    lines = ["# Grocery List", ""]
    for category in sorted(by_category):
        lines.append(f"## {category.title()}")
        for item in sorted(by_category[category], key=lambda entry: entry.item):
            quantity = f"{item.quantity:.2f}".rstrip("0").rstrip(".")
            if not quantity:
                quantity = "0"
            unit = f" {item.unit}" if item.unit else ""
            lines.append(f"- {item.item} — {quantity}{unit}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
