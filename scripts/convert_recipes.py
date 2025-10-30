"""Convert unstructured recipe files into the structured recipe schema using an LLM."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from jsonschema.protocols import Validator
from openai import OpenAI

from mealplanner.models import Recipe

SUPPORTED_INPUT_EXTENSIONS = {
    ".txt",
    ".md",
    ".rst",
    ".markdown",
    ".text",
}


@dataclass
class ConversionArgs:
    input_dir: Path
    output_dir: Path
    schema_path: Path
    model: str
    temperature: float
    max_output_tokens: int
    max_retries: int
    retry_delay: float
    overwrite: bool
    dry_run: bool
    raw_output_dir: Optional[Path]
    error_output_dir: Optional[Path]
    use_responses: bool


@dataclass
class LLMConfig:
    client: OpenAI
    schema: dict
    validator: Validator
    system_prompt: str


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert recipe files into the Meal Planner recipe schema using an OpenAI-compatible endpoint.",
    )
    parser.add_argument("input_dir", type=Path, help="Directory containing raw recipe files (txt, md, rst).")
    parser.add_argument("output_dir", type=Path, help="Directory where structured recipe JSON files will be written.")
    parser.add_argument(
        "--schema-path",
        type=Path,
        default=Path("schemas/recipe.schema.json"),
        help="Path to the recipe JSON schema used for validation.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
        help="Model name to request from the OpenAI-compatible endpoint.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature passed to the model.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=1200,
        help="Maximum number of output tokens requested from the model (Responses API).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retries when the model request fails.",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="Base delay in seconds between retries; doubled after each failure.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OPENAI_BASE_URL"),
        help="Override the base URL for the OpenAI-compatible API.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENAI_API_KEY"),
        help="API key used for authentication. Defaults to the OPENAI_API_KEY environment variable.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite JSON files if they already exist in the output directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the LLM and validation steps without writing any JSON files.",
    )
    parser.add_argument(
        "--raw-output-dir",
        type=Path,
        help="Optional directory to dump the raw LLM JSON output for inspection.",
    )
    parser.add_argument(
        "--error-output-dir",
        type=Path,
        help="Optional directory where validation failures and raw model output will be stored.",
    )
    parser.add_argument(
        "--use-responses",
        action="store_true",
        help="Use the Responses API instead of the Chat Completions API.",
    )
    parser.add_argument(
        "--system-prompt",
        default=None,
        help="Custom system prompt to guide the LLM. Defaults to a built-in instruction block.",
    )
    return parser


def _load_schema(schema_path: Path) -> dict:
    try:
        with schema_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except OSError as exc:
        raise SystemExit(f"Unable to read schema at {schema_path}: {exc}")


def _create_validator(schema: dict) -> Validator:
    return Draft202012Validator(schema)


def _create_client(api_key: Optional[str], base_url: Optional[str]) -> OpenAI:
    kwargs = {}
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def _iter_recipe_sources(input_dir: Path) -> Iterator[Path]:
    for path in sorted(input_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS:
            yield path


def _build_system_prompt(custom_prompt: Optional[str], schema: dict) -> str:
    if custom_prompt:
        return custom_prompt

    meals = ", ".join(sorted({"breakfast", "lunch", "dinner", "snack"}))
    base_prompt = (
        "You are a meticulous sous-chef that converts recipe notes into structured data for a meal planning app.\n"
        "Follow these rules strictly:\n"
        "- Respond with JSON that matches the provided schema exactly.\n"
        "- Use lowercase strings for meal types and tags.\n"
        "- Represent quantities as decimal numbers (floats).\n"
        "- Produce boolean values for yes/no fields.\n"
        f"- Allowed meal types: {meals}.\n"
        "- Include every ingredient with quantity, unit, and grocery category when possible.\n"
        "- Leave produces_leftovers and leftovers_replace_meal unset; they will be reviewed manually later.\n"
        "- Use empty strings instead of null when a textual field is unknown.\n"
        "If information is missing, make a reasonable inference and note it in tags."
    )

    schema_summary = json.dumps(schema, indent=2, ensure_ascii=False)
    return f"{base_prompt}\n\nJSON Schema:\n{schema_summary}"


def _build_user_prompt(source_path: Path, content: str) -> str:
    return (
        "Convert the following recipe into a JSON object that follows the provided schema. "
        "Use best judgement to fill in missing numeric values.\n"
        f"Source file: {source_path.name}\n"
        "Recipe text:\n"
        f"""{content}"""
    )


def _request_json(
    args: ConversionArgs,
    config: LLMConfig,
    user_prompt: str,
) -> str:
    delay = args.retry_delay
    for attempt in range(1, args.max_retries + 1):
        try:
            if not args.use_responses:
                response = config.client.chat.completions.create(
                    model=args.model,
                    messages=[
                        {"role": "system", "content": config.system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=args.temperature,
                    max_tokens=args.max_output_tokens,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content or ""
            else:
                response = config.client.responses.create(
                    model=args.model,
                    input=[
                        {"role": "system", "content": config.system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=args.temperature,
                    max_output_tokens=args.max_output_tokens,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {"name": "recipe", "schema": config.schema},
                    },
                )
                content = response.output_text or ""
            if not content:
                raise ValueError("Empty response from model")
            return content
        except Exception as exc:  # noqa: BLE001
            logging.warning("Model request failed on attempt %s/%s: %s", attempt, args.max_retries, exc)
            if attempt == args.max_retries:
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("Exhausted retries without receiving a response")


def _parse_recipes(raw_json: str, source_path: Path, validator: Validator) -> List[Recipe]:
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse JSON for {source_path}: {exc}") from exc

    if isinstance(data, dict):
        payloads: Iterable[dict] = [data]
    elif isinstance(data, list):
        payloads = data
    else:
        raise ValueError(f"Model output for {source_path} must be a JSON object or list of objects")

    recipes: List[Recipe] = []
    for entry in payloads:
        try:
            validator.validate(entry)
        except ValidationError as exc:
            raise ValueError(f"Schema validation failed for {source_path}: {exc.message}") from exc
        recipe = Recipe.from_dict(entry)
        recipes.append(recipe)
    return recipes


def _write_recipe(recipe: Recipe, output_path: Path, overwrite: bool, dry_run: bool) -> None:
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {output_path}")
    if dry_run:
        logging.info("[dry-run] Would write %s", output_path)
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload_dict = recipe.to_dict()
    payload_dict.pop("produces_leftovers", None)
    payload_dict.pop("leftovers_replace_meal", None)
    payload = json.dumps(payload_dict, indent=2, ensure_ascii=False) + "\n"
    output_path.write_text(payload, encoding="utf-8")
    logging.info("Wrote %s", output_path)


def _dump_raw_output(raw_output_dir: Optional[Path], source_path: Path, raw_content: str, dry_run: bool) -> None:
    if not raw_output_dir:
        return
    destination = raw_output_dir / source_path.with_suffix(".json").name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        logging.info("[dry-run] Would save raw output to %s", destination)
        return
    destination.write_text(raw_content + "\n", encoding="utf-8")


def _dump_error_output(
    error_output_dir: Optional[Path],
    relative_path: Path,
    raw_content: str,
    error_message: str,
    dry_run: bool,
) -> None:
    if not error_output_dir:
        return

    destination = error_output_dir / relative_path
    destination = destination.with_suffix(".json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    error_path = destination.with_suffix(".error.txt")

    if dry_run:
        logging.info(
            "[dry-run] Would save failed output to %s and error details to %s",
            destination,
            error_path,
        )
        return

    destination.write_text(raw_content + "\n", encoding="utf-8")
    error_path.write_text(error_message + "\n", encoding="utf-8")


def convert_recipes() -> None:
    parser = _create_parser()
    ns = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    args = ConversionArgs(
        input_dir=ns.input_dir,
        output_dir=ns.output_dir,
        schema_path=ns.schema_path,
        model=ns.model,
        temperature=ns.temperature,
        max_output_tokens=ns.max_output_tokens,
        max_retries=ns.max_retries,
        retry_delay=ns.retry_delay,
        overwrite=ns.overwrite,
        dry_run=ns.dry_run,
        raw_output_dir=ns.raw_output_dir,
        error_output_dir=ns.error_output_dir,
        use_responses=ns.use_responses,
    )

    if not args.input_dir.exists():
        parser.error(f"Input directory does not exist: {args.input_dir}")
    if not args.input_dir.is_dir():
        parser.error(f"Input path must be a directory: {args.input_dir}")

    if args.raw_output_dir:
        args.raw_output_dir.mkdir(parents=True, exist_ok=True)
    if args.error_output_dir:
        args.error_output_dir.mkdir(parents=True, exist_ok=True)

    schema = _load_schema(args.schema_path)
    validator = _create_validator(schema)

    client = _create_client(ns.api_key, ns.base_url)
    system_prompt = _build_system_prompt(ns.system_prompt, schema)
    llm_config = LLMConfig(client=client, schema=schema, validator=validator, system_prompt=system_prompt)

    sources = list(_iter_recipe_sources(args.input_dir))
    if not sources:
        logging.info("No recipe files found in %s", args.input_dir)
        return

    logging.info("Found %d recipe files", len(sources))

    for source_path in sources:
        logging.info("Processing %s", source_path)
        content = source_path.read_text(encoding="utf-8")
        user_prompt = _build_user_prompt(source_path, content)
        raw_json = _request_json(args, llm_config, user_prompt)
        _dump_raw_output(args.raw_output_dir, source_path, raw_json, args.dry_run)

        try:
            recipes = _parse_recipes(raw_json, source_path, validator)
        except ValueError as exc:
            logging.error("Failed to validate %s: %s", source_path, exc)
            relative_path = source_path.relative_to(args.input_dir)
            _dump_error_output(
                args.error_output_dir,
                relative_path,
                raw_json,
                str(exc),
                args.dry_run,
            )
            continue
        for index, recipe in enumerate(recipes, start=1):
            relative = source_path.relative_to(args.input_dir)
            output_path = args.output_dir / relative
            output_path = output_path.with_suffix(".json")
            if len(recipes) > 1:
                output_path = output_path.with_name(f"{output_path.stem}_{index}{output_path.suffix}")
            try:
                _write_recipe(recipe, output_path, args.overwrite, args.dry_run)
            except FileExistsError as exc:
                logging.warning(str(exc))


if __name__ == "__main__":
    try:
        convert_recipes()
    except Exception as exc:  # noqa: BLE001
        logging.error("%s", exc)
        sys.exit(1)
