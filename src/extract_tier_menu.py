"""List every item inside a host region's tier tabs.

The game's construction menu is one asset (25000035 by default). Each host
region has a node under Values/ConstructionMenu/RegionMenu, and each node has
a CategoryMode/Tier/Categories list. This tool walks those tier tabs and writes
the leaves, nested submenus and tab IDs that the menu gate has to lock.

Usage:
  python src/extract_tier_menu.py --assets "<path to assets.xml>" \
      --preset presets/new_world.json \
      --out presets/items/new_world_core.json

Run it again after a game update if the vanilla menu changes. The item lists
under presets/items/ are generated with this tool and shipped so most users
never need to run it.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    ITEMS_DIR,
    ToolError,
    as_guid,
    fail,
    info,
    load_preset,
    preset_tab_guids,
    write_json,
)


def index_categories(assets_path: Path) -> dict[str, dict]:
    """Read assets.xml once and keep the ConstructionCategory assets."""
    index: dict[str, dict] = {}
    for _event, element in ET.iterparse(assets_path, events=("end",)):
        if element.tag != "Asset":
            continue
        standard = element.find("Values/Standard")
        guid = (standard.findtext("GUID") or "").strip() if standard is not None else ""
        if not guid:
            element.clear()
            continue
        if element.findtext("Template") != "ConstructionCategory":
            element.clear()
            continue
        children: list[str] = []
        building_list = element.find("Values/ConstructionCategory/BuildingList")
        if building_list is not None:
            for item in building_list.findall("Item"):
                child = (item.findtext("Building") or item.findtext("Category") or "").strip()
                if child.isdigit():
                    children.append(child)
        index[guid] = {
            "name": (standard.findtext("Name") or "").strip(),
            "children": children,
        }
        element.clear()
    return index


def expand(guid: str, index: dict[str, dict], depth: int = 0, seen: set[str] | None = None) -> tuple[set[str], set[str]]:
    """Return (leaves, nested submenus) below one GUID."""
    seen = seen if seen is not None else set()
    if guid in seen or depth > 12:
        return set(), set()
    seen.add(guid)
    entry = index.get(guid)
    if entry is None or not entry["children"]:
        return {guid}, set()
    leaves: set[str] = set()
    containers: set[str] = {guid} if depth > 0 else set()
    for child in entry["children"]:
        child_leaves, child_containers = expand(child, index, depth + 1, seen)
        leaves |= child_leaves
        containers |= child_containers
    return leaves, containers


def build(assets_path: Path, preset: dict) -> dict:
    index = index_categories(assets_path)
    tab_guids = preset_tab_guids(preset)
    tab_names = {as_guid(tab["guid"]): tab.get("name", "") for tab in preset["tier_tabs"]}

    all_leaves: set[str] = set()
    all_containers: set[str] = set()
    tabs: list[dict] = []
    for guid in tab_guids:
        if guid not in index:
            raise ToolError(
                f"tier tab {guid} was not found in {assets_path}. "
                "The game may have changed, or the preset is for another version."
            )
        leaves, containers = expand(guid, index)
        all_leaves |= leaves
        all_containers |= containers
        tabs.append(
            {
                "guid": guid,
                "name": tab_names.get(guid) or index[guid]["name"],
                "internal_name": index[guid]["name"],
                "leaves": sorted(leaves, key=int),
                "containers": sorted(containers, key=int),
            }
        )

    locked = set(all_leaves) | set(all_containers) | set(tab_guids)
    return {
        "schema_version": 1,
        "region": preset["key"],
        "display_name": preset.get("display_name", preset["key"]),
        "menu_guid": as_guid(preset["menu_guid"]),
        "region_node": preset["region_node"],
        "tabs": tabs,
        "leaves": sorted(all_leaves, key=int),
        "containers": sorted(all_containers, key=int),
        "totals": {
            "tabs": len(tab_guids),
            "leaves": len(all_leaves),
            "containers": len(all_containers),
            "locked_items": len(locked),
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--assets", required=True, help="Path to the game's exported assets.xml")
    parser.add_argument("--preset", required=True, help="Preset key (new_world) or path to a preset JSON")
    parser.add_argument("--out", help="Write the item list here instead of printing it")
    parser.add_argument("--quiet", action="store_true", help="Only print errors")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        preset, _preset_path = load_preset(args.preset)
        result = build(Path(args.assets), preset)
    except FileNotFoundError as error:
        fail(f"file not found: {error.filename}")
    except ToolError as error:
        fail(str(error))

    if args.out:
        write_json(Path(args.out), result)
        if not args.quiet:
            totals = result["totals"]
            info(
                f"{result['display_name']}: {totals['tabs']} tabs, "
                f"{totals['leaves']} leaves, {totals['containers']} submenus, "
                f"{totals['locked_items']} items to lock"
            )
        info(f"wrote {args.out}")
    else:
        import json

        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
