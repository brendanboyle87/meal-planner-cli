# Meal Planner CLI — SPEC

Version: 1.0  
Targets: macOS (Apple Silicon), Python 3.11+  
Outputs: Markdown weekly plan, CSV grocery list  
Destination: Apple Notes (via Shortcut or AppleScript)

## Goals
- Plan Sun–Sat (breakfast, lunch, dinner, snack) from a recipe library.
- Avoid repeats across a variability window.
- Respect per-day cook-time limits; allow skipped meals.
- Optional Sunday meal-prep (≤ 1–2h) and reuse yielded prep items.
- Export Markdown (plan) and CSV (groceries).
- Easy append to Apple Notes.

## CLI (intended)
```
mealplanner plan   --recipes data/recipes.json   --config configs/week_config.json   --history history/history.json   --out-md out/plan_YYYY-MM-DD.md   --out-json out/plan_YYYY-MM-DD.json   [--seed 42]

mealplanner groceries   --recipes data/recipes.json   --plan out/plan_YYYY-MM-DD.json   --config configs/week_config.json   --out-csv out/groceries_YYYY-MM-DD.csv   --out-md out/groceries_YYYY-MM-DD.md
```
Use `osascript scripts/push_to_notes.scpt "Meal Plan (YYYY-MM-DD)" "Personal" out/plan_*.md out/groceries_*.md` to append both to Apple Notes.
