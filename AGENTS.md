# Agent Guidelines for Meal Planner CLI

This file applies to the entire repository.

## Project overview
- The CLI entrypoint lives in `mealplanner/cli.py`; tests are under `tests/`.
- Recipes, configs, and schemas used by the CLI live in `data/`, `configs/`, and `schemas/` respectively.
- `scripts/convert_recipes.py` converts unstructured recipes using an LLM. Refer to `README.md` for invocation details.

## Development workflow
- Prefer using [uv](https://docs.astral.sh/uv/) for dependency management. Run commands like `uv run mealplanner --help` or `uv run pytest` from the repo root.
- If uv is unavailable, a standard `pip install -e .` followed by `pytest` is acceptable.
- Keep imports sorted logically (standard library, third-party, local) and ensure all new modules include module-level docstrings when appropriate.
- Write functions and public APIs with complete type hints. Avoid adding try/except wrappers around imports.

## Testing expectations
- Execute `uv run pytest` before finishing work whenever tests exist for the touched areas.
- When adding new features, update or create tests under `tests/` to cover the behavior.

## Documentation and PR notes
- Update `README.md`, `SPEC.md`, or relevant docs when introducing user-visible changes.
- When writing PR summaries, concisely list user-facing impacts and mention affected commands or scripts when relevant.
