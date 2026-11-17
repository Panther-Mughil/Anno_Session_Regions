import json
from pathlib import Path

from common import ITEMS_DIR, PRESETS_DIR

EXPECTED = {
    "new_world": {"tabs": 3, "leaves": 101, "containers": 8, "locked": 112, "streets": [101308, 101309]},
    "old_world": {"tabs": 7, "leaves": 135, "containers": 8, "locked": 150, "streets": [1000178, 1010035]},
    "arctic": {"tabs": 2, "leaves": 31, "containers": 3, "locked": 36, "streets": [112113]},
    "enbesa": {"tabs": 2, "leaves": 58, "containers": 5, "locked": 65, "streets": [114523, 119029]},
}


def test_presets_and_item_lists_match() -> None:
    for key, expected in EXPECTED.items():
        preset = json.loads((PRESETS_DIR / f"{key}.json").read_text(encoding="utf-8"))
        items = json.loads((ITEMS_DIR / f"{key}_core.json").read_text(encoding="utf-8"))
        assert preset["key"] == key
        assert preset["menu_guid"] == 25000035
        assert len(preset["tier_tabs"]) == expected["tabs"]
        assert preset["street_assets"] == expected["streets"]
        assert items["totals"]["tabs"] == expected["tabs"]
        assert items["totals"]["leaves"] == expected["leaves"]
        assert items["totals"]["containers"] == expected["containers"]
        assert items["totals"]["locked_items"] == expected["locked"]
        for street in expected["streets"]:
            assert str(street) in items["leaves"]


def test_only_the_new_world_is_marked_tested() -> None:
    for key in EXPECTED:
        preset = json.loads((PRESETS_DIR / f"{key}.json").read_text(encoding="utf-8"))
        assert preset["tested_in_game"] is (key == "new_world")
