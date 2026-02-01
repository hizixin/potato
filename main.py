"""Calculate daily calories from menu.yaml and nutrition_facts.md."""

import logging
import sys
from nutrition import NutritionDB, Nutrients, KCAL_PER_G
from menu import Menu

DAYS = ["upper", "lower", "rest"]


def check_menu(db, menu):
    """Check all menu items exist in the database."""
    missing = [item for item in menu.all_items() if not db.exists(item)]
    if missing:
        raise ValueError(
            "Not found in nutrition_facts.md:\n"
            + "\n".join(f"   - {m}" for m in missing)
        )

    for id, n in menu.choose_groups.items():
        opts = [g for g, _, i in menu.options if i == id]
        if len(opts) < n:
            raise ValueError(f"[choose {n}] has only {len(opts)} option(s)")


def get_nutrients(db, items):
    """Get nutrients for item(s). Averages if multiple."""
    return Nutrients.avg([db.get(item) for item in items])


def calculate(db, menu, day):
    """Calculate total nutrients for a day."""
    totals = Nutrients()

    # Fixed items
    for group in menu.fixed:
        totals = totals + get_nutrients(db, group)

    # Options: group by id, average all options, multiply by N
    grouped = {}
    for group, n, id in menu.options:
        grouped.setdefault(id, (n, []))[1].append(get_nutrients(db, group))

    for _, (n, choices) in grouped.items():
        totals = totals + Nutrients.avg(choices) * n

    # Per-day carbs (e.g., brown rice)
    if menu.carbs_item and (grams := menu.carbs_per_day.get(day)):
        totals = totals + db.get(f"{grams}g {menu.carbs_item}")

    # Extra from YAML (add calories from c/p/f)
    extra = menu.extra
    extra_cal = (
        extra.c * KCAL_PER_G["c"]
        + extra.p * KCAL_PER_G["p"]
        + extra.f * KCAL_PER_G["f"]
    )
    totals = totals + Nutrients(
        c=extra.c, p=extra.p, f=extra.f, cal=extra.cal + extra_cal
    )

    return totals


def format_row(day, totals):
    """Format as markdown table row."""
    c_cal = totals.c * KCAL_PER_G["c"]
    p_cal = totals.p * KCAL_PER_G["p"]
    f_cal = totals.f * KCAL_PER_G["f"]
    total_cal = p_cal + c_cal + f_cal

    return (
        f"| {day.capitalize()} | {totals.cal:.0f} kcal | "
        f"{totals.c:.0f}g ({c_cal/total_cal*100:.0f}%) | "
        f"{totals.p:.0f}g ({p_cal/total_cal*100:.0f}%) | "
        f"{totals.f:.0f}g ({f_cal/total_cal*100:.0f}%) |"
    )


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        db = NutritionDB("nutrition_facts.md")
        menu = Menu("menu.yaml")
        check_menu(db, menu)

        rows = [
            "| Day | Calories | Carbs | Protein | Fat |",
            "|-----|----------|-------|---------|-----|",
        ]
        for day in DAYS:
            t = calculate(db, menu, day)
            rows.append(format_row(day, t))

        output = "\n".join(rows)
        logging.info(output)
        with open("out.md", "w") as f:
            f.write(output + "\n")
    except ValueError as e:
        logging.error(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
