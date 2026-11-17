"""Find what installed mods add to a host region's construction menu.

The scanner reads the mod folders directly. It does not read mod-loader.log,
because that log only describes the last launch and misses anything downloaded
since.

It looks in the places the loader scans:
  * <game install>/mods
  * Documents/Anno 1800/mods inside the Wine or Windows user folder
  * C:/users/Public/mod.io/4169/mods

Pass --game-dir on Linux, because the install can live on any mount. The
Documents and mod.io folders are found automatically inside common Wine and
Steam prefixes.

The output is a compatibility list for generate.py --compat. This is the
experimental part of the toolkit: it understands the common ModOp forms, and it
warns when it cannot follow a mod. Locking an extra item is harmless. Missing
one leaves that item visible in the custom session.

Usage:
  python src/scan_mods.py --preset new_world --game-dir "/path/to/Anno 1800" \
      --assets "/path/to/assets.xml" --out compat.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
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
    read_json,
    version_key,
    warn,
    write_json,
)
from version import __version__  # noqa: E402

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache"}
ADD_TYPES = {"add", "addnextsibling", "addprevsibling", "insert", "merge"}
REMOVE_TYPES = {"remove"}
MODIO_APP_ID = "4169"
STEAM_APP_ID = "916440"


# ---------------------------------------------------------------------------
# Mod roots


def wine_drive_c_roots() -> list[Path]:
    home = Path.home()
    roots: list[Path] = []
    for prefix in (
        home / ".steam/steam/steamapps/compatdata" / STEAM_APP_ID / "pfx",
        home / ".local/share/Steam/steamapps/compatdata" / STEAM_APP_ID / "pfx",
        home / ".var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/compatdata" / STEAM_APP_ID / "pfx",
    ):
        drive_c = prefix / "drive_c"
        if drive_c.is_dir():
            roots.append(drive_c)
    for drive_c in (home / ".wine/drive_c",):
        if drive_c.is_dir():
            roots.append(drive_c)
    games = home / "Games"
    if games.is_dir():
        roots.extend(path for path in games.glob("*/drive_c") if path.is_dir())
    return roots


def documents_roots() -> list[Path]:
    home = Path.home()
    candidates: list[Path] = []
    if os.name == "nt":
        candidates.append(Path(os.environ.get("USERPROFILE", home)) / "Documents/Anno 1800/mods")
    else:
        candidates.append(home / "Documents/Anno 1800/mods")
        for drive_c in wine_drive_c_roots():
            users = drive_c / "users"
            if users.is_dir():
                candidates.extend(path / "Documents/Anno 1800/mods" for path in users.iterdir() if path.is_dir())
    return [path for path in candidates if path.is_dir()]


def modio_roots() -> list[Path]:
    candidates: list[Path] = []
    if os.name == "nt":
        candidates.append(Path(f"C:/users/Public/mod.io/{MODIO_APP_ID}/mods"))
    for drive_c in wine_drive_c_roots():
        candidates.append(drive_c / f"users/Public/mod.io/{MODIO_APP_ID}/mods")
    return [path for path in candidates if path.is_dir()]


def install_roots(game_dir: str | None) -> list[Path]:
    candidates: list[Path] = []
    if game_dir:
        candidates.append(Path(game_dir) / "mods")
    env = os.environ.get("ANNO_GAME_DIR")
    if env:
        candidates.append(Path(env) / "mods")
    if os.name == "nt":
        for base in (
            Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Ubisoft/Ubisoft Game Launcher/games/Anno 1800/mods",
            Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Steam/steamapps/common/Anno 1800/mods",
        ):
            candidates.append(base)
    return [path for path in candidates if path.is_dir()]


def resolve_roots(args: argparse.Namespace) -> tuple[list[Path], list[Path]]:
    found: list[Path] = []
    missing: list[Path] = []
    explicit: list[Path] = []
    for raw in args.mods_root or []:
        explicit.append(Path(raw))
    for raw in (args.documents, args.modio):
        if raw:
            explicit.append(Path(raw))
    if args.game_dir:
        explicit.append(Path(args.game_dir) / "mods")

    candidates = list(explicit)
    if not args.no_autodetect:
        candidates.extend(documents_roots())
        candidates.extend(modio_roots())
        candidates.extend(install_roots(args.game_dir))
    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.is_dir():
            found.append(path)
        else:
            missing.append(path)
    return found, missing


def read_activations(root: Path) -> set[str]:
    path = root / "activations.json"
    if not path.exists():
        return set()
    try:
        data = read_json(path)
    except (OSError, json.JSONDecodeError):
        warn(f"could not read {path}; disabled mods in it will be scanned")
        return set()
    values = data.get("disabledIds", []) if isinstance(data, dict) else []
    return {str(value) for value in values}


def mod_name(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("English") or next(iter(value.values()), "") or "")
    return ""


def discover_mods(roots: list[Path]) -> tuple[list[dict], list[str]]:
    mods: list[dict] = []
    warnings: list[str] = []
    queue = list(roots)
    seen_roots: set[str] = set()
    while queue:
        root = queue.pop(0)
        try:
            resolved = str(root.resolve())
        except OSError:
            resolved = str(root)
        if resolved in seen_roots:
            continue
        seen_roots.add(resolved)
        disabled = read_activations(root)
        seen_dirs: set[str] = set()
        for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
            current = Path(dirpath)
            try:
                resolved_dir = str(current.resolve())
            except OSError:
                resolved_dir = str(current)
            if resolved_dir in seen_dirs:
                dirnames[:] = []
                continue
            seen_dirs.add(resolved_dir)
            dirnames[:] = sorted(name for name in dirnames if name not in SKIP_DIRS)
            if "modinfo.json" in filenames:
                try:
                    data = read_json(current / "modinfo.json")
                except (OSError, json.JSONDecodeError) as error:
                    warnings.append(f"could not read {current / 'modinfo.json'}: {error}")
                    continue
                if not isinstance(data, dict):
                    warnings.append(f"{current / 'modinfo.json'} is not an object")
                    continue
                mod_id = str(data.get("ModID") or current.name)
                if not data.get("ModID"):
                    warnings.append(f"{current} has no ModID; using the folder name")
                mods.append(
                    {
                        "path": current,
                        "root": root,
                        "mod_id": mod_id,
                        "version": str(data.get("Version", "0")),
                        "name": mod_name(data.get("ModName")) or mod_id,
                        "disabled": current.name.startswith("-") or mod_id in disabled,
                    }
                )
            for name in filenames:
                if name.lower().endswith(".lnk"):
                    target = (current / name).read_text(encoding="utf-8", errors="ignore").strip()
                    if target:
                        link = Path(target)
                        if not link.is_absolute():
                            link = (current / link).resolve()
                        if link.is_dir():
                            queue.append(link)
                        # Other .lnk files link individual game files, not mod
                        # folders. Ignore them.
                elif name.lower().endswith(".zip") and current == root:
                    warnings.append(f"{current / name}: zip mods are not scanned; extract the folder to use it")
    return mods, warnings


def dedupe_mods(mods: list[dict]) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    chosen: dict[str, dict] = {}
    order: list[str] = []
    for mod in mods:
        mod_id = mod["mod_id"]
        if mod_id not in chosen:
            chosen[mod_id] = mod
            order.append(mod_id)
            continue
        old = chosen[mod_id]
        old_key = version_key(old["version"])
        new_key = version_key(mod["version"])
        if new_key > old_key:
            warnings.append(
                f"{mod_id}: using version {mod['version']} from {mod['root']} "
                f"instead of {old['version']} from {old['root']}"
            )
            chosen[mod_id] = mod
        elif new_key == old_key:
            warnings.append(
                f"{mod_id}: version {mod['version']} appears in more than one folder; "
                f"last scanned wins ({mod['root']}). The loader's tie order is not documented."
            )
            chosen[mod_id] = mod
        else:
            warnings.append(
                f"{mod_id}: ignoring older version {mod['version']} from {mod['root']}"
            )
    return [chosen[mod_id] for mod_id in order], warnings


# ---------------------------------------------------------------------------
# XML reading


def xml_files(mod_path: Path) -> list[Path]:
    files: list[Path] = []
    seen_dirs: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(mod_path, followlinks=True):
        current = Path(dirpath)
        try:
            resolved_dir = str(current.resolve())
        except OSError:
            resolved_dir = str(current)
        if resolved_dir in seen_dirs:
            dirnames[:] = []
            continue
        seen_dirs.add(resolved_dir)
        if current != mod_path and "modinfo.json" in filenames:
            dirnames[:] = []
            continue
        dirnames[:] = sorted(name for name in dirnames if name not in SKIP_DIRS)
        files.extend(current / name for name in sorted(filenames) if name.lower().endswith(".xml"))
    return files


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def text_of(element: ET.Element, path: str) -> str:
    return (element.findtext(path) or "").strip()


def category_children(asset: ET.Element) -> list[str]:
    children: list[str] = []
    for building in asset.iter():
        if local_name(building.tag) not in ("Building", "Category"):
            continue
        value = (building.text or "").strip()
        if value.isdigit():
            children.append(value)
    return list(dict.fromkeys(children))


def asset_definitions(element: ET.Element, mod_id: str) -> dict[str, dict]:
    """Find ConstructionCategory assets in a ModOp payload."""
    result: dict[str, dict] = {}
    for asset in element.iter():
        if local_name(asset.tag) != "Asset":
            continue
        template = text_of(asset, "Template")
        if template != "ConstructionCategory":
            continue
        standard = asset.find("Values/Standard")
        if standard is None:
            continue
        guid = (standard.findtext("GUID") or "").strip()
        if not guid.isdigit():
            continue
        result[guid] = {
            "guid": guid,
            "name": (standard.findtext("Name") or "").strip(),
            "children": category_children(asset),
            "source_mod": mod_id,
        }
    return result


def load_vanilla(assets_path: Path) -> tuple[dict[str, dict], dict[str, str]]:
    """Return (category definitions, GUID -> name) from a vanilla assets.xml."""
    categories: dict[str, dict] = {}
    names: dict[str, str] = {}
    for _event, element in ET.iterparse(assets_path, events=("end",)):
        if element.tag != "Asset":
            continue
        standard = element.find("Values/Standard")
        guid = (standard.findtext("GUID") or "").strip() if standard is not None else ""
        if not guid:
            element.clear()
            continue
        name = (standard.findtext("Name") or "").strip()
        if name:
            names[guid] = name
        if element.findtext("Template") == "ConstructionCategory":
            categories[guid] = {
                "guid": guid,
                "name": name,
                "children": category_children(element),
                "source_mod": "vanilla",
            }
        element.clear()
    return categories, names


def selector_guids(path: str) -> list[str]:
    return re.findall(r"(?:Category|Building)\s*=\s*['\"]?(\d+)", path, flags=re.IGNORECASE)


def region_path(path: str, region_node: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    return f"regionmenu/{region_node.lower()}" in normalized


def classify(modop: ET.Element, scope: set[str], region_node: str) -> tuple[str, str | None]:
    """Say whether a ModOp changes something inside a tier tab or adds a new tab.

    addNextSibling and addPrevSibling insert a sibling next to the anchor. A path
    that anchors on Item[Category='<tier tab>'] under Tier/Categories therefore
    adds a new tab next to the tier tabs. A path that works on a category's
    BuildingList changes what is inside a tab.
    """
    modop_type = (modop.get("Type") or "").strip().lower()
    target = (modop.get("GUID") or "").strip() or None
    path = (modop.get("Path") or "").replace("\\", "/")
    path_lower = path.lower()
    in_region = region_path(path, region_node)
    if not in_region and (target is None or target not in scope):
        return "ignore", target

    tier_level = "categorymode/tier/categories" in path_lower
    selectors = selector_guids(path)

    if tier_level:
        if selectors and any(selected in scope for selected in selectors):
            if modop_type in ("addnextsibling", "addprevsibling"):
                return "new_tab", selectors[0]
            if modop_type in ("add", "insert", "merge"):
                return "inside", selectors[0]
        if modop_type in ("add", "insert", "merge") and not selectors:
            return "new_tab", target

    if target in scope:
        return "inside", target
    for selected in selectors:
        if selected in scope:
            if tier_level:
                return "new_tab", selected
            return "inside", selected
    return "ignore", target


def scan_mod(mod: dict, region_node: str, scope: set[str], vanilla: dict[str, dict]) -> dict:
    defs: dict[str, dict] = {}
    direct_in_scope: list[dict] = []
    new_tabs: list[dict] = []
    removed: list[dict] = []
    warnings: list[str] = []

    for path in xml_files(mod["path"]):
        try:
            tree = ET.parse(path)
        except ET.ParseError as error:
            warnings.append(f"{path}: not valid XML ({error})")
            continue
        for element in tree.getroot().iter():
            if local_name(element.tag) != "ModOp":
                continue
            modop_type = (element.get("Type") or "").strip().lower()
            modop_path = (element.get("Path") or "").replace("\\", "/")

            # Category definitions can sit on a ModOp that targets an unrelated
            # anchor, so collect them before deciding whether the ModOp changes
            # the menu.
            for guid, definition in asset_definitions(element, mod["mod_id"]).items():
                defs[guid] = definition
                if guid in scope:
                    direct_in_scope.append(
                        {"guid": guid, "source_mod": mod["mod_id"], "reason": "category defined inside a tier tab"}
                    )

            kind, anchor = classify(element, scope, region_node)
            if kind == "ignore":
                continue

            if modop_type in REMOVE_TYPES:
                for selected in selector_guids(modop_path) or ([anchor] if anchor else []):
                    removed.append(
                        {
                            "guid": selected,
                            "source_mod": mod["mod_id"],
                            "reason": f"removed from tier tab {anchor or 'selected tab'}",
                        }
                    )
                continue
            if modop_type not in ADD_TYPES:
                continue

            buildings: list[str] = []
            categories: list[str] = []
            for item in element:
                if local_name(item.tag) != "Item":
                    continue
                for child in item.iter():
                    tag = local_name(child.tag)
                    value = (child.text or "").strip()
                    if not value.isdigit():
                        continue
                    if tag == "Building":
                        buildings.append(value)
                    elif tag == "Category":
                        categories.append(value)

            if kind == "inside":
                for guid in buildings + categories:
                    direct_in_scope.append(
                        {
                            "guid": guid,
                            "source_mod": mod["mod_id"],
                            "reason": f"added inside tier tab {anchor or 'selected tab'}",
                        }
                    )
            elif kind == "new_tab":
                for guid in categories:
                    new_tabs.append(
                        {
                            "guid": guid,
                            "source_mod": mod["mod_id"],
                            "reason": "added as a new tab next to the tier tabs",
                        }
                    )
                if buildings:
                    warnings.append(
                        f"{path}: a Building was added at the tier list level; the scanner could not place it"
                    )
    return {
        "mod": mod,
        "defs": defs,
        "direct": direct_in_scope,
        "new_tabs": new_tabs,
        "removed": removed,
        "warnings": warnings,
    }


def expand(seed: list[dict], defs: dict[str, dict], vanilla: dict[str, dict], names: dict[str, str]) -> list[dict]:
    items: dict[str, dict] = {}
    stack = list(seed)
    seen: set[str] = set()
    while stack:
        entry = stack.pop()
        guid = entry["guid"]
        if guid in seen:
            continue
        seen.add(guid)
        definition = defs.get(guid) or vanilla.get(guid)
        items.setdefault(
            guid,
            {
                "guid": int(guid),
                "name": (definition or {}).get("name") or names.get(guid, ""),
                "source_mod": entry["source_mod"],
                "reason": entry["reason"],
            },
        )
        if definition is None:
            continue
        for child in definition.get("children", []):
            stack.append({"guid": child, "source_mod": entry["source_mod"], "reason": f"inside {guid}"})
    return [items[guid] for guid in sorted(items, key=int)]


def build(args: argparse.Namespace) -> dict:
    preset, _preset_path = load_preset(args.preset)
    tier_tabs = set(preset_tab_guids(preset))
    item_path = ITEMS_DIR / f"{preset['key']}_core.json"
    scope = set(tier_tabs)
    if item_path.exists():
        data = read_json(item_path)
        scope.update(as_guid(guid) for guid in data.get("containers", []))
        scope.update(as_guid(tab["guid"]) for tab in data.get("tabs", []) if isinstance(tab, dict))
    else:
        warn(f"no shipped item list for {preset['key']}; only the tier tabs are in scope")

    vanilla: dict[str, dict] = {}
    vanilla_names: dict[str, str] = {}
    if args.assets:
        vanilla, vanilla_names = load_vanilla(Path(args.assets))
    else:
        warn("--assets was not given; nested vanilla categories inside a tier tab cannot be expanded")

    roots, missing = resolve_roots(args)
    if not roots:
        raise ToolError(
            "no mod folders found. Pass --game-dir and/or --mods-root. "
            "Use --print-roots to see what was checked."
        )
    mods, discover_warnings = discover_mods(roots)
    mods, dedupe_warnings = dedupe_mods(mods)
    warnings = discover_warnings + dedupe_warnings
    selected = mods if args.include_disabled else [mod for mod in mods if not mod["disabled"]]

    scans = [scan_mod(mod, preset["region_node"], scope, vanilla) for mod in selected]
    definitions: dict[str, dict] = {}
    for scan in scans:
        definitions.update(scan["defs"])
    direct = [entry for scan in scans for entry in scan["direct"]]
    new_tabs = [entry for scan in scans for entry in scan["new_tabs"]]
    removed = [entry for scan in scans for entry in scan["removed"]]
    for scan in scans:
        warnings.extend(scan["warnings"])

    for entry in new_tabs + removed:
        definition = definitions.get(entry["guid"]) or vanilla.get(entry["guid"])
        entry["name"] = (definition or {}).get("name") or vanilla_names.get(entry["guid"], "")
        entry["guid"] = int(entry["guid"])

    items = expand(direct, definitions, vanilla, vanilla_names)

    return {
        "schema_version": 1,
        "toolkit_version": __version__,
        "region": preset["key"],
        "region_node": preset["region_node"],
        "tier_tabs": sorted(tier_tabs, key=int),
        "roots": {
            "found": [str(path) for path in roots],
            "missing": [str(path) for path in missing],
        },
        "mods": [
            {
                "mod_id": mod["mod_id"],
                "version": mod["version"],
                "name": mod["name"],
                "path": str(mod["path"]),
                "root": str(mod["root"]),
                "enabled": not mod["disabled"],
            }
            for mod in mods
        ],
        "items": items,
        "new_tabs": new_tabs,
        "removed": removed,
        "warnings": warnings,
        "notes": [
            "items are safe to over-include: locking an asset that is not in the menu does nothing",
            "new_tabs are not locked; add them by hand if the custom session should hide them",
        ],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preset", required=True, help="Region preset key or path")
    parser.add_argument("--assets", help="Path to assets.xml, used to expand nested vanilla categories")
    parser.add_argument("--game-dir", help="Anno 1800 install folder (the tool reads <game-dir>/mods)")
    parser.add_argument("--mods-root", action="append", help="Extra mod folder to scan; repeat for more")
    parser.add_argument("--documents", help="Documents/Anno 1800/mods folder, if auto-detection misses it")
    parser.add_argument("--modio", help="mod.io mods folder, if auto-detection misses it")
    parser.add_argument("--no-autodetect", action="store_true", help="Only scan the folders you pass")
    parser.add_argument("--include-disabled", action="store_true", help="Scan mods that are disabled in activations.json")
    parser.add_argument("--out", help="Write the compatibility list here instead of printing it")
    parser.add_argument("--print-roots", action="store_true", help="Print the folders that were found and exit")
    parser.add_argument("--strict", action="store_true", help="Exit with code 1 if there are warnings")
    parser.add_argument("--quiet", action="store_true", help="Only print errors")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.print_roots:
            roots, missing = resolve_roots(args)
            for path in roots:
                info(f"found: {path}")
            for path in missing:
                info(f"missing: {path}")
            if not roots:
                warn("no mod folders found")
            return 0
        result = build(args)
    except FileNotFoundError as error:
        fail(f"file not found: {error.filename}")
    except ToolError as error:
        fail(str(error))

    if args.include_disabled:
        for mod in result["mods"]:
            if not mod["enabled"]:
                warn(f"including disabled mod {mod['mod_id']}")
    if args.out:
        write_json(Path(args.out), result)
    else:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    if not args.quiet:
        info(
            f"{result['region']}: {len(result['items'])} mod items, "
            f"{len(result['new_tabs'])} new tabs, {len(result['mods'])} mods, "
            f"{len(result['warnings'])} warnings"
        )
        if args.out:
            info(f"wrote {args.out}")
    if args.strict and result["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
