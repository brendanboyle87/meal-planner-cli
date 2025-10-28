# Meal Planner Spec Bundle

This bundle contains SPEC.md, minimal example data/config, JSON Schemas, and an AppleScript bridge to append outputs to Apple Notes.

## Quick Start
1. Drop this folder into your repo.
2. Implement the CLI as described in SPEC.md.
3. After generating Markdown in `out/`:
   ```bash
   osascript scripts/push_to_notes.scpt "Meal Plan (2025-11-02)" "Personal" out/plan_2025-11-02.md out/groceries_2025-11-02.md
   ```
