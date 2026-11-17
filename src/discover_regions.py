"""Draft presets from the region menus in a game's assets.xml.

Use this after a game update or when you want to support a host region that
does not ship with the toolkit. It reads the ConstructionMenu asset, walks every
RegionMenu node, and writes one draft preset per node.

The draft preset has the menu node and tier tabs filled in. Street assets and
host sessions are filled in only for the four regions the toolkit knows today.
Fill the rest by hand from Streets Unified and your map data.

Usage:
  python src/discover_regions.py --assets "<path to assets.xml>" \
      --out-dir presets/drafts
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ToolError, fail, info, write_json  # noqa: E402

FRIENDLY = {
    "farmer": "Farmers",
    "worker": "Workers",
    "artisan": "Artisans",
    "engineer": "Engineers",
    "investor": "Investors",
    "scholar": "Scholars",
    "tourist": "Tourists",
    "jornalero": "Jornaleros",
    "obrero": "Obreros",
    "artista": "Artistas",
    "explorer": "Explorers",
    "technician": "Technicians",
    "shepherd": "Shepherds",
    "elder": "Elders",
}

KNOWN = {
    "Moderate": {
        "key": "old_world",
        "display_name": "Old World",
        "host_sessions": [{"guid": 180023, "name": "Old World"}],
        "related_sessions": [{"guid": 110934, "name": "Cape Trelawney"}],
        "street_assets": [1000178, 1010035],
    },
    "Colony01": {
        "key": "new_world",
        "display_name": "New World",
        "host_sessions": [{"guid": 180025, "name": "New World"}],
        "related_sessions": [],
        "street_assets": [101308, 101309],
    },
    "Arctic": {
        "key": "arctic",
        "display_name": "Arctic",
        "host_sessions": [{"guid": 180045, "name": "Arctic"}],
        "related_sessions": [],
        "street_assets": [112113],
    },
    "Africa": {
        "key": "enbesa",
        "display_name": "Enbesa",
        "host_sessions": [{"guid": 112132, "name": "Enbesa"}],
        "related_sessions": [],
        "street_assets": [114523, 119029],
    },
}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def friendly_name(standard: ET.Element | None, fallback: str) -> str:
    if standard is None:
        return fallback
    icon = (standard.findtext("IconFilename") or "").strip()
    stem = icon.rsplit("/", 1)[-1].removesuffix(".png")
    stem = stem.removeprefix("icon_workforce_2d_").removeprefix("icon_")
    return FRIENDLY.get(stem, (standard.findtext("Name") or fallback).strip())


def read_menu(assets_path: Path, menu_guid: str) -> tuple[ET.Element, dict[str, dict]]:
    menu = None
    categories: dict[str, dict] = {}
    for _event, element in ET.iterparse(assets_path, events=("end",)):
        if element.tag != "Asset":
            continue
        standard = element.find("Values/Standard")
        guid = (standard.findtext("GUID") or "").strip() if standard is not None else ""
        if not guid:
            element.clear()
            continue
        if guid == menu_guid:
            menu = element
            continue
        if element.findtext("Template") == "ConstructionCategory":
            children: list[str] = []
            building_list = element.find("Values/ConstructionCategory/BuildingList")
            if building_list is not None:
                for item in building_list.findall("Item"):
                    child = (item.findtext("Building") or item.findtext("Category") or "").strip()
                    if child.isdigit():
                        children.append(child)
            categories[guid] = {"name": friendly_name(standard, guid), "children": children}
        element.clear()
    if menu is None:
        raise ToolError(f"construction menu {menu_guid} was not found in {assets_path}")
    return menu, categories


def expand(guid: str, categories: dict[str, dict], depth: int = 0, seen: set[str] | None = None) -> tuple[set[str], set[str]]:
    seen = seen if seen is not None else set()
    if guid in seen or depth > 12:
        return set(), set()
    seen.add(guid)
    entry = categories.get(guid)
    if entry is None or not entry["children"]:
        return {guid}, set()
    leaves: set[str] = set()
    containers: set[str] = {guid} if depth > 0 else set()
    for child in entry["children"]:
        child_leaves, child_containers = expand(child, categories, depth + 1, seen)
        leaves |= child_leaves
        containers |= child_containers
    return leaves, containers


def build_drafts(assets_path: Path, menu_guid: str) -> list[dict]:
    menu, categories = read_menu(assets_path, menu_guid)
    region_menu = menu.find("Values/ConstructionMenu/RegionMenu")
    if region_menu is None:
        raise ToolError(f"menu {menu_guid} has no RegionMenu node")

    drafts: list[dict] = []
    for region in region_menu:
        known = KNOWN.get(region.tag, {})
        tier_list = region.find("CategoryMode/Tier/Categories")
        if tier_list is None:
            continue
        tabs: list[dict] = []
        ignored: list[dict] = []
        for item in tier_list.findall("Item"):
            guid = (item.findtext("Category") or "").strip()
            if not guid.isdigit():
                continue
            name = categories.get(guid, {}).get("name", guid)
            if name.startswith("CreativeMode"):
                ignored.append({"guid": int(guid), "name": name})
                continue
            leaves, containers = expand(guid, categories)
            tabs.append(
                {
                    "guid": int(guid),
                    "name": name,
                    "leaves": len(leaves),
                    "containers": len(containers),
                }
            )
        drafts.append(
            {
                "schema_version": 1,
                "key": known.get("key", slug(region.tag)),
                "display_name": known.get("display_name", region.tag),
                "menu_guid": int(menu_guid),
                "region_node": region.tag,
                "host_sessions": known.get("host_sessions", []),
                "related_sessions": known.get("related_sessions", []),
                "tier_tabs": [{"guid": tab["guid"], "name": tab["name"]} for tab in tabs],
                "street_assets": known.get("street_assets", []),
                "tested_in_game": False,
                "notes": (
                    "Draft from discover_regions.py. Fill host_sessions and "
                    "street_assets before use."
                ),
                "counts": {tab["guid"]: {"leaves": tab["leaves"], "containers": tab["containers"]} for tab in tabs},
                "ignored_categories": ignored,
            }
        )
    return drafts


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--assets", required=True, help="Path to the game's exported assets.xml")
    parser.add_argument("--menu-guid", default="25000035", help="ConstructionMenu asset GUID (default: 25000035)")
    parser.add_argument("--out-dir", default="presets/drafts", help="Folder for the draft presets")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        drafts = build_drafts(Path(args.assets), args.menu_guid)
    except FileNotFoundError as error:
        fail(f"file not found: {error.filename}")
    except ToolError as error:
        fail(str(error))

    out_dir = Path(args.out_dir)
    for draft in drafts:
        path = out_dir / f"{draft['key']}.json"
        write_json(path, draft)
        tabs = ", ".join(f"{tab['guid']} {tab['name']}" for tab in draft["tier_tabs"])
        info(f"{path}: {draft['region_node']} -> {len(draft['tier_tabs'])} tabs ({tabs})")
        if draft["ignored_categories"]:
            names = ", ".join(item["name"] for item in draft["ignored_categories"])
            info(f"  ignored non-tier categories: {names}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
