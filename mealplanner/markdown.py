"""Render Markdown outputs for plans and groceries."""

from __future__ import annotations

from typing import Dict, List

def build_plan_markdown(plan: dict) -> str:
    week_start = plan.get("week_start_date", "")
    lines: List[str] = [f"# Meal Plan — Week of {week_start}", ""]

    for day in plan.get("days", []):
        lines.append(f"## {day['day_name']} ({day['date']})")
        meals = day.get("meals", [])
        for meal in meals:
            meal_type = meal.get("meal_type", "").title()
            recipe = meal.get("recipe_name") or "(skipped)"
            total_time = meal.get("total_time_min")
            if total_time is not None:
                lines.append(f"- **{meal_type}:** {recipe} ({total_time:.0f} min total)")
            else:
                lines.append(f"- **{meal_type}:** {recipe}")
        lines.append("")

    summary = plan.get("summary", {})
    prep_items: Dict[str, List[str]] = summary.get("yielded_prep_items", {})
    if prep_items:
        lines.append("## Meal Prep Summary")
        for prep_item, sources in sorted(prep_items.items()):
            lines.append(f"- {prep_item}: made in {', '.join(sorted(set(sources)))}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
