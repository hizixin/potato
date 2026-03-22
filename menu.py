"""Parse menu.yaml into structured data."""

import re
import yaml
from dataclasses import dataclass, field
from nutrition import Nutrients, parse_quantity


@dataclass
class Carbs:
    """Per-day carb grams with an optional weighted blend."""

    grams: dict = field(default_factory=dict)  # {day: float}
    blend: dict = field(default_factory=dict)  # {name: weight 0.0–1.0}

    def for_day(self, day):
        """Return [(grams, item_name), ...] for a given day."""
        total = self.grams.get(day)
        if not total:
            return []
        return [(total * w, name) for name, w in self.blend.items()]

    @property
    def names(self):
        return list(self.blend.keys())


class Menu:
    """Loads menu.yaml: fixed items, choose-N options, per-day carbs, extras."""

    RESERVED_KEYS = {"carbs", "extra"}

    def __init__(self, filepath):
        self.extra = Nutrients()
        self._carbs = []
        self.fixed = []  # [(items, ...)]
        self.options = []  # [(items, n, group_id)]
        self.choose_groups = {}  # {group_id: n}

        self._load(filepath)

    def _load(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._parse_extra(data.get("extra"))
        self._parse_carbs(data.get("carbs"))
        self._parse_sections(data)

    def _parse_extra(self, extra):
        """Parse extra: section."""
        if not extra:
            return
        self.extra = Nutrients(
            c=extra.get("carbs", 0),
            p=extra.get("protein", 0),
            f=extra.get("fat", 0),
            cal=extra.get("calories", 0),
        )

    def _parse_carbs(self, carbs):
        """Parse carbs: section (per-day grams + optional blend)."""
        if not carbs:
            return
        for key, vals in carbs.items():
            pcts = vals.get("blend")

            if pcts:
                total = sum(pcts.values())
                if total != 100:
                    raise ValueError(
                        f"carbs.{key}.blend: percentages sum to {total}%, expected 100%"
                    )
                blend = {f"{n} {key}": p / 100 for n, p in pcts.items()}
            else:
                blend = {key: 1.0}

            self._carbs.append(
                Carbs(
                    grams={
                        d: parse_quantity(str(v))[0]
                        for d, v in vals.get("grams", {}).items()
                    },
                    blend=blend,
                )
            )

    def _parse_sections(self, data):
        """Parse food sections. Supports 2 levels of nesting."""
        choose_id = 0

        for section, items in data.items():
            if section in self.RESERVED_KEYS or not isinstance(items, list):
                continue

            for item in items:
                if isinstance(item, str):
                    self.fixed.append([item])
                    continue

                for key, opts in item.items():
                    if m := re.match(r"choose\s+(\d+)", key):
                        choose_id += 1
                        n = int(m.group(1))
                        self.choose_groups[choose_id] = n

                        for opt in opts or []:
                            if isinstance(opt, str):
                                self.options.append(([opt], n, choose_id))
                            elif isinstance(opt, dict):
                                nested = list(opt.values())[0]
                                self.options.append((nested, n, choose_id))

    def carbs_for_day(self, day):
        """Return [(grams, item_name), ...] for a given day."""
        result = []
        for c in self._carbs:
            result.extend(c.for_day(day))
        return result

    def all_items(self):
        """All food items (for validation)."""
        items = []
        for group in self.fixed:
            items.extend(group)
        for group, _, _ in self.options:
            items.extend(group)
        for c in self._carbs:
            items.extend(c.names)
        return items
