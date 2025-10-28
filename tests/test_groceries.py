from __future__ import annotations

from mealplanner.groceries import build_grocery_markdown, build_grocery_table, collect_grocery_items
from mealplanner.models import Recipe, WeekConfig


def make_recipe() -> Recipe:
    return Recipe.from_dict(
        {
            "id": "dinner_1",
            "name": "Pasta",
            "meals": ["dinner"],
            "prep_time_min": 10,
            "cook_time_min": 20,
            "servings_per_recipe": 2,
            "ingredients": [
                {"item": "pasta", "qty": 200, "unit": "g", "category": "grains"},
                {"item": "tomato sauce", "qty": 1, "unit": "jar", "category": "pantry"},
                {"item": "water", "qty": 2, "unit": "cups", "category": "pantry"},
            ],
        }
    )


def make_config() -> WeekConfig:
    return WeekConfig.from_dict(
        {
            "week_start_date": "2025-01-12",
            "people": 4,
            "variability_window_weeks": 2,
            "max_daily_cook_times": {"Sunday": {"dinner": 60}},
            "skip_meals": {},
            "enable_meal_prep_sunday": False,
            "meal_prep_max_minutes": None,
            "preferred_prep_items": [],
            "pantry": ["water"],
        }
    )


def make_plan() -> dict:
    return {
        "week_start_date": "2025-01-12",
        "days": [
            {
                "day_name": "Sunday",
                "date": "2025-01-12",
                "meals": [
                    {
                        "meal_type": "dinner",
                        "recipe_id": "dinner_1",
                        "recipe_name": "Pasta",
                        "total_time_min": 30,
                    }
                ],
            },
            {
                "day_name": "Monday",
                "date": "2025-01-13",
                "meals": [
                    {
                        "meal_type": "dinner",
                        "recipe_id": "dinner_1",
                        "recipe_name": "Pasta",
                        "total_time_min": 30,
                    }
                ],
            },
        ],
    }


def test_collect_grocery_items_scales_for_people():
    recipe = make_recipe()
    plan = make_plan()
    config = make_config()

    items = collect_grocery_items(plan, [recipe], config)
    assert len(items) == 2

    pasta = next(item for item in items if item.item == "pasta")
    # 200g per recipe, 4 people -> multiplier 2, used twice in plan -> 800g total
    assert abs(pasta.quantity - 800) < 1e-6

    table = build_grocery_table(items)
    assert "pasta" in table
    assert "800.00" in table

    markdown = build_grocery_markdown(items)
    assert "# Grocery List" in markdown
    assert "pasta" in markdown
    assert "tomato sauce" in markdown
    assert "water" not in markdown
