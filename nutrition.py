"""Nutrition database and nutrient calculations."""

import logging
import re
from dataclasses import dataclass

KCAL_PER_G = {"c": 4, "p": 4, "f": 9}


@dataclass
class Nutrients:
    """Carbs, protein, fat, and calories."""

    c: float = 0
    p: float = 0
    f: float = 0
    cal: float = 0

    def __add__(self, other):
        return Nutrients(
            self.c + other.c, self.p + other.p, self.f + other.f, self.cal + other.cal
        )

    def __mul__(self, n):
        return Nutrients(self.c * n, self.p * n, self.f * n, self.cal * n)

    def __truediv__(self, n):
        return Nutrients(self.c / n, self.p / n, self.f / n, self.cal / n)

    @staticmethod
    def avg(items):
        """Average a list of Nutrients."""
        total = Nutrients()
        for item in items:
            total = total + item
        return total / len(items)


def parse_quantity(text):
    """Parse '110g chicken' -> (110, 'g', 'chicken')."""
    text = text.strip().lower()

    # "half X" -> 0.5
    if text.startswith("half "):
        return 0.5, None, text[5:]

    # Pattern: number + optional unit (g/cup) + item
    if m := re.match(r"^(\d+(?:\.\d+)?)\s*(g|cup)?\s*(.+)$", text):
        return float(m.group(1)), m.group(2), m.group(3)

    return 1, None, text


class NutritionDB:
    """Loads nutrition_facts.md and looks up nutrients by food name."""

    def __init__(self, filepath):
        self.items = {}
        self._load(filepath)

    def _load(self, filepath):
        """Load from markdown table."""
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines[2:]:  # skip header and separator
            if not line.strip() or "|" not in line:
                continue
            cols = [c.strip() for c in line.split("|")[1:-1]]
            if len(cols) >= 8:
                name = cols[1].lower()
                self.items[name] = {
                    "c": float(cols[2]),
                    "p": float(cols[3]),
                    "f": float(cols[4]),
                    "serving_amt": float(cols[5]),
                    "serving_unit": cols[6].lower(),
                    "cal": float(cols[7]),
                }

    def match(self, text):
        """Find best matching food by word overlap."""
        text = text.lower().strip()

        if text in self.items:
            return text

        text_words = set(text.split())
        best, best_score = None, 0

        for name in self.items:
            name_words = set(name.split())
            overlap = len(text_words & name_words)
            score = overlap / len(name_words) if name_words else 0
            if score > best_score:
                best, best_score = name, score

        return best if best_score > 0.5 else None

    def get(self, menu_text):
        """Look up nutrients for '110g chicken breast', scaled by portion."""
        qty, unit, item_text = parse_quantity(menu_text)
        name = self.match(item_text)

        if not name:
            raise ValueError(f"Item not found: {menu_text}")

        item = self.items[name]

        # Calculate ratio
        if unit == "g" and item["serving_unit"] == "g":
            ratio = qty / item["serving_amt"]
        elif unit == item["serving_unit"]:
            ratio = qty / item["serving_amt"]
        elif unit is None:
            ratio = qty / item["serving_amt"]
        else:
            logging.warning(
                f"Unit mismatch for '{menu_text}': expected '{item['serving_unit']}', got '{unit}'"
            )
            ratio = qty

        return Nutrients(
            c=item["c"] * ratio,
            p=item["p"] * ratio,
            f=item["f"] * ratio,
            cal=item["cal"] * ratio,
        )

    def exists(self, menu_text):
        """Check if menu item can be matched."""
        _, _, item_text = parse_quantity(menu_text)
        return self.match(item_text) is not None
