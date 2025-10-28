"""Command line interface for the meal planner application."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .groceries import (
    build_grocery_markdown,
    build_grocery_table,
    collect_grocery_items,
)
from .history import HistoryStore
from .io import load_config, load_plan_json, load_recipes
from .markdown import build_plan_markdown
from .planner import generate_plan


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mealplanner",
        description="Generate weekly meal plans and grocery lists.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser(
        "plan", help="Generate a meal plan for the configured week."
    )
    plan_parser.add_argument("--recipes", required=True, type=Path)
    plan_parser.add_argument("--config", required=True, type=Path)
    plan_parser.add_argument("--history", type=Path)
    plan_parser.add_argument("--out-md", required=True, type=Path)
    plan_parser.add_argument("--out-json", required=True, type=Path)
    plan_parser.add_argument("--seed", type=int)

    groceries_parser = subparsers.add_parser(
        "groceries",
        help="Generate grocery outputs based on an existing meal plan.",
    )
    groceries_parser.add_argument("--recipes", required=True, type=Path)
    groceries_parser.add_argument("--plan", required=True, type=Path)
    groceries_parser.add_argument("--config", required=True, type=Path)
    groceries_parser.add_argument("--out-csv", required=True, type=Path)
    groceries_parser.add_argument("--out-md", required=True, type=Path)

    return parser


def _write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json_file(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _handle_plan(
    recipes_path: Path,
    config_path: Path,
    history_path: Optional[Path],
    out_md: Path,
    out_json: Path,
    seed: Optional[int],
) -> int:
    recipes = load_recipes(recipes_path)
    config = load_config(config_path)

    history_store: Optional[HistoryStore]
    if history_path is not None:
        history_store = HistoryStore(history_path)
        history = history_store.load()
    else:
        history_store = None
        history = None

    plan = generate_plan(recipes, config, history, seed=seed)
    plan_markdown = build_plan_markdown(plan)

    _write_json_file(out_json, plan)
    _write_text_file(out_md, plan_markdown)

    if history_store is not None:
        history_store.record_plan(plan, config)

    return 0


def _handle_groceries(
    recipes_path: Path,
    plan_path: Path,
    config_path: Path,
    out_csv: Path,
    out_md: Path,
) -> int:
    recipes = load_recipes(recipes_path)
    config = load_config(config_path)
    plan = load_plan_json(plan_path)

    grocery_items = collect_grocery_items(plan, recipes, config)
    grocery_table = build_grocery_table(grocery_items)
    grocery_markdown = build_grocery_markdown(grocery_items)

    _write_text_file(out_csv, grocery_table)
    _write_text_file(out_md, grocery_markdown)

    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = _create_parser()
    args = parser.parse_args(argv)

    if args.command == "plan":
        return _handle_plan(
            recipes_path=args.recipes,
            config_path=args.config,
            history_path=args.history,
            out_md=args.out_md,
            out_json=args.out_json,
            seed=args.seed,
        )

    if args.command == "groceries":
        return _handle_groceries(
            recipes_path=args.recipes,
            plan_path=args.plan,
            config_path=args.config,
            out_csv=args.out_csv,
            out_md=args.out_md,
        )

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":  # pragma: no cover - exercised via tests
    sys.exit(main())
