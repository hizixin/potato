"""Parse menu.yaml into structured data."""

import re
import yaml
from nutrition import Nutrients, parse_quantity


class Menu:
    """Loads menu.yaml: fixed items, choose-N options, per-day carbs, extras."""

    RESERVED_KEYS = {"carbs", "extra"}

    def __init__(self, filepath):
        self.extra = Nutrients()
        self.carbs_per_day = {}
        self.carbs_item = None
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
        """Parse carbs: section (per-day amounts)."""
        if not carbs:
            return
        for item_name, amounts in carbs.items():
            self.carbs_item = item_name
            self.carbs_per_day = {
                day: parse_quantity(str(val))[0] for day, val in amounts.items()
            }

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

    def all_items(self):
        """All food items (for validation)."""
        items = []
        for group in self.fixed:
            items.extend(group)
        for group, _, _ in self.options:
            items.extend(group)
        if self.carbs_item:
            items.append(self.carbs_item)
        return items
