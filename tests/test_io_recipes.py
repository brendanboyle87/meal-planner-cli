from __future__ import annotations

import json

from mealplanner.io import load_recipes


def _recipe_dict(recipe_id: str) -> dict:
    return {
        "id": recipe_id,
        "name": f"Recipe {recipe_id}",
        "meals": ["dinner"],
        "prep_time_min": 10,
        "cook_time_min": 20,
        "servings_per_recipe": 4,
        "yields_prep_item": [],
        "ingredients": [
            {
                "item": "ingredient",
                "qty": 1,
                "unit": "unit",
                "category": "general",
            }
        ],
    }


def test_load_recipes_from_directory(tmp_path):
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()

    single_recipe_path = recipes_dir / "single.json"
    single_recipe_path.write_text(json.dumps(_recipe_dict("one")))

    multi_recipe_path = recipes_dir / "multi.json"
    multi_recipe_path.write_text(
        json.dumps([_recipe_dict("two"), _recipe_dict("three")])
    )

    nested_dir = recipes_dir / "nested"
    nested_dir.mkdir()
    nested_recipe_path = nested_dir / "nested.json"
    nested_recipe_path.write_text(json.dumps(_recipe_dict("four")))

    recipes = load_recipes(recipes_dir)

    recipe_ids = {recipe.id for recipe in recipes}
    assert recipe_ids == {"one", "two", "three", "four"}


def test_load_recipes_from_single_recipe_file(tmp_path):
    recipe_path = tmp_path / "recipe.json"
    recipe_path.write_text(json.dumps(_recipe_dict("solo")))

    recipes = load_recipes(recipe_path)

    assert [recipe.id for recipe in recipes] == ["solo"]
