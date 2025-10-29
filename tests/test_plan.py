from __future__ import annotations

from mealplanner.models import Recipe, WeekConfig
from mealplanner.planner import generate_plan


def _recipe(
    *,
    recipe_id: str,
    name: str,
    meals: list[str],
    prep: float,
    cook: float,
    servings: float,
    yields: list[str] | None = None,
    produces_leftovers: bool = False,
    leftovers_meal: str | None = None,
):
    return Recipe.from_dict(
        {
            "id": recipe_id,
            "name": name,
            "meals": meals,
            "prep_time_min": prep,
            "cook_time_min": cook,
            "servings_per_recipe": servings,
            "produces_leftovers": produces_leftovers,
            "leftovers_replace_meal": leftovers_meal,
            "yields_prep_item": yields or [],
            "ingredients": [
                {
                    "item": f"{recipe_id}_ingredient",
                    "qty": 1,
                    "unit": "unit",
                    "category": "general",
                }
            ],
        }
    )


def make_recipes() -> list[Recipe]:
    return [
        _recipe(recipe_id="breakfast_1", name="Toast", meals=["breakfast"], prep=5, cook=2, servings=1),
        _recipe(recipe_id="breakfast_2", name="Oatmeal", meals=["breakfast"], prep=4, cook=6, servings=1),
        _recipe(recipe_id="lunch_1", name="Salad", meals=["lunch"], prep=10, cook=0, servings=1),
        _recipe(recipe_id="lunch_2", name="Soup", meals=["lunch"], prep=15, cook=10, servings=2, yields=["soup_stock"]),
        _recipe(
            recipe_id="dinner_1",
            name="Pasta",
            meals=["dinner"],
            prep=10,
            cook=20,
            servings=2,
            produces_leftovers=True,
            leftovers_meal="lunch",
        ),
        _recipe(
            recipe_id="dinner_2",
            name="Stir Fry",
            meals=["dinner"],
            prep=20,
            cook=20,
            servings=2,
            yields=["veggies"],
        ),
        _recipe(recipe_id="snack_1", name="Fruit", meals=["snack"], prep=2, cook=0, servings=1),
        _recipe(recipe_id="snack_2", name="Yogurt", meals=["snack"], prep=2, cook=0, servings=1),
    ]


def make_config() -> WeekConfig:
    config_dict = {
        "week_start_date": "2025-01-12",
        "variability_window_weeks": 4,
        "allow_high_effort_dinner": {
            "Sunday": False,
            "Monday": True,
            "Tuesday": False,
            "Wednesday": False,
            "Thursday": False,
            "Friday": True,
            "Saturday": True,
        },
        "skip_meals": {"Tuesday": ["snack"]},
        "enable_meal_prep_sunday": True,
        "meal_prep_max_minutes": 120,
        "preferred_prep_items": ["soup_stock"],
        "pantry": [],
    }
    return WeekConfig.from_dict(config_dict)


def test_generate_plan_respects_history_and_skips():
    recipes = make_recipes()
    config = make_config()
    history = {"2025-01-05": ["breakfast_1"]}

    plan = generate_plan(recipes, config, history, seed=7)

    assert plan["week_start_date"] == "2025-01-12"
    assert len(plan["days"]) == 7

    for day in plan["days"]:
        if day["day_name"] == "Tuesday":
            snack_entry = next(meal for meal in day["meals"] if meal["meal_type"] == "snack")
            assert snack_entry["recipe_id"] is None
        breakfast_recipes = [meal["recipe_id"] for meal in day["meals"] if meal["meal_type"] == "breakfast"]
        for recipe_id in breakfast_recipes:
            assert recipe_id != "breakfast_1"

    monday = next(day for day in plan["days"] if day["day_name"] == "Monday")
    monday_lunch = next(meal for meal in monday["meals"] if meal["meal_type"] == "lunch")
    assert monday_lunch["is_leftover"] is True
    assert monday_lunch["leftover_source_name"] == "Pasta"
    assert monday_lunch["recipe_id"] is None

    summary = plan["summary"]
    assert "veggies" in summary["yielded_prep_items"]


def test_generate_plan_produces_markdown_order():
    recipes = make_recipes()
    config = make_config()

    plan = generate_plan(recipes, config, history=None, seed=1)
    first_day = plan["days"][0]
    assert first_day["day_name"] == "Sunday"
    assert {meal["meal_type"] for meal in first_day["meals"]} == {"breakfast", "lunch", "dinner", "snack"}

    dinner = next(meal for meal in first_day["meals"] if meal["meal_type"] == "dinner")
    # Sunday dinner disallows high effort so should pick the lower-effort option
    assert dinner["recipe_name"] == "Pasta"
