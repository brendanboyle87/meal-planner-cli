from __future__ import annotations

import json
from pathlib import Path
import sys
import types

try:  # pragma: no cover - optional dependency shim for tests
    import jsonschema  # type: ignore  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - fallback for test environment
    jsonschema_stub = types.ModuleType("jsonschema")
    jsonschema_stub.Draft202012Validator = object

    exceptions_module = types.ModuleType("jsonschema.exceptions")

    class _ValidationError(Exception):
        """Minimal stand-in for jsonschema.exceptions.ValidationError."""

        ...

    exceptions_module.ValidationError = _ValidationError

    protocols_module = types.ModuleType("jsonschema.protocols")
    protocols_module.Validator = object

    jsonschema_stub.exceptions = exceptions_module
    jsonschema_stub.protocols = protocols_module

    sys.modules["jsonschema"] = jsonschema_stub
    sys.modules["jsonschema.exceptions"] = exceptions_module
    sys.modules["jsonschema.protocols"] = protocols_module

try:  # pragma: no cover - optional dependency shim for tests
    from openai import OpenAI  # type: ignore  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - fallback for test environment
    openai_stub = types.ModuleType("openai")

    class _OpenAI:  # noqa: D401 - minimal placeholder
        """Placeholder OpenAI client used for import-time wiring in tests."""

        def __init__(self, *args, **kwargs) -> None:  # noqa: D401
            ...

    openai_stub.OpenAI = _OpenAI
    sys.modules["openai"] = openai_stub

from mealplanner.models import Recipe
from scripts.convert_recipes import _dump_error_output, _write_recipe


def test_write_recipe_omits_leftover_fields(tmp_path):
    recipe = Recipe.from_dict(
        {
            "id": "leftover-test",
            "name": "Leftover Test",
            "meals": ["dinner"],
            "prep_time_min": 15,
            "cook_time_min": 30,
            "servings_per_recipe": 4,
            "produces_leftovers": True,
            "leftovers_replace_meal": "lunch",
            "yields_prep_item": [],
            "ingredients": [
                {
                    "item": "beans",
                    "qty": 1,
                    "unit": "can",
                    "category": "pantry",
                }
            ],
        }
    )

    output_path = tmp_path / "recipe.json"
    _write_recipe(recipe, output_path, overwrite=True, dry_run=False)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "produces_leftovers" not in payload
    assert "leftovers_replace_meal" not in payload


def test_dump_error_output_writes_files(tmp_path):
    error_dir = tmp_path / "errors"
    relative_path = Path("subdir/recipe.txt")
    raw_content = "{\"foo\": \"bar\"}"
    message = "Schema validation failed"

    _dump_error_output(error_dir, relative_path, raw_content, message, dry_run=False)

    expected_json = error_dir / "subdir" / "recipe.json"
    expected_txt = error_dir / "subdir" / "recipe.error.txt"

    assert expected_json.exists()
    assert expected_txt.exists()
    assert expected_json.read_text(encoding="utf-8").strip() == raw_content
    assert expected_txt.read_text(encoding="utf-8").strip() == message
