"""Build a session menu gate from a config file and a region preset.

The generated mod has three parts:
  * modinfo.json, with the Streets Unified dependency
  * data/config/export/main/asset/assets.xml, the session triggers
  * data/script/<prefix>_<module>_{hide,show,creative}.lua, the lock lists

Each module is independent. The core module covers the base game, and every
compatibility module covers one group of installed mods, so a problem in one
module cannot break the other modules.

Usage:
  python src/generate.py --config examples/new_world/config.json
  python src/generate.py --config examples/new_world/config.json \
      --compat compat.json --out out/new_world
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from string import Template

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    TEMPLATES_DIR,
    ToolError,
    as_guid,
    fail,
    guid_list,
    info,
    load_preset,
    load_sessions,
    preset_street_guids,
    read_item_file,
    read_json,
    warn,
    write_json,
    write_text,
)
from version import __version__  # noqa: E402

TOOLKIT_NAME = "Anno Session Regions"
DEFAULT_INCLUDE = ["leaves", "containers", "tabs"]
LANGUAGES = (
    "Chinese",
    "English",
    "French",
    "German",
    "Italian",
    "Japanese",
    "Korean",
    "Polish",
    "Russian",
    "Spanish",
    "Taiwanese",
)


def localized(value: str) -> dict:
    """All 11 modinfo language keys, with the English value filled in."""
    return {language: (value if language == "English" else None) for language in LANGUAGES}


def load_templates() -> dict[str, Template]:
    names = {
        "hide": "hide.lua",
        "show": "show.lua",
        "creative": "creative.lua",
        "trigger": "trigger.xml",
        "sub_not_creative": "sub_not_creative.xml",
        "sub_creative": "sub_creative.xml",
    }
    result: dict[str, Template] = {}
    for key, name in names.items():
        path = TEMPLATES_DIR / name
        if not path.exists():
            raise ToolError(f"template missing: {path}")
        result[key] = Template(path.read_text(encoding="utf-8"))
    return result


def item_guids_from_file(path: Path, include: list[str]) -> list[str]:
    data = read_item_file(path)
    items: list[object] = []
    for key in include:
        if key == "tabs":
            for tab in data.get("tabs", []):
                items.append(tab.get("guid"))
        else:
            items.extend(data.get(key, []))
    return guid_list(items, f"item GUID in {path}")


def collect_module_items(module: dict, config_dir: Path, preset: dict, compat: dict | None) -> list[str]:
    items: list[object] = []
    items_file = module.get("items_file")
    if items_file:
        path = Path(items_file)
        if not path.is_absolute():
            path = config_dir / path
        if not path.exists():
            raise ToolError(f"items file not found: {path}")
        items.extend(item_guids_from_file(path, module.get("include", DEFAULT_INCLUDE)))
    items.extend(module.get("items", []))
    if module.get("key") == "compat" and compat is not None:
        for entry in compat.get("items", []):
            items.append(entry.get("guid") if isinstance(entry, dict) else entry)

    keep = set(guid_list(module.get("keep_unlocked", preset_street_guids(preset)), "keep_unlocked"))
    exclude = set(guid_list(module.get("exclude", []), "exclude"))
    seen: set[str] = set()
    result: list[str] = []
    for value in items:
        guid = as_guid(value)
        if guid in keep or guid in exclude or guid in seen:
            continue
        seen.add(guid)
        result.append(guid)
    return sorted(result, key=int)


def lua_values(values: list[str], per_line: int = 12) -> str:
    lines = []
    for start in range(0, len(values), per_line):
        lines.append("    " + ", ".join(values[start : start + per_line]))
    return ",\n".join(lines)


def resolve_show_sessions(config: dict, hide: dict) -> list[dict]:
    hide_guid = as_guid(hide["guid"], "hide session GUID")
    raw = config.get("show_sessions")
    if raw is None:
        sessions = [s for s in load_sessions() if as_guid(s["guid"]) != hide_guid]
    else:
        sessions = raw
    result: list[dict] = []
    seen: set[str] = set()
    for session in sessions:
        guid = as_guid(session["guid"], "show session GUID")
        if guid == hide_guid:
            raise ToolError("hide_session must not appear in show_sessions")
        if guid in seen:
            continue
        seen.add(guid)
        result.append({"guid": guid, "name": session.get("name", guid)})
    if not result:
        raise ToolError("no show sessions: the menu would never be restored")
    return result


def validate_config(config: dict) -> None:
    for field in ("mod_id", "mod_name", "hide_session", "script_prefix", "modules"):
        if field not in config:
            raise ToolError(f"config is missing: {field}")
    if "trigger_guid_base" not in config or config["trigger_guid_base"] in (None, "", 0, "0"):
        raise ToolError(
            "trigger_guid_base is empty. Choose the first free GUID in your own "
            "range and put it in the config, or pass --guid-base."
        )
    try:
        base = int(config["trigger_guid_base"])
    except (TypeError, ValueError):
        raise ToolError("trigger_guid_base must be a number")
    if not 0 < base <= 2147483647:
        raise ToolError("trigger_guid_base must be between 1 and 2147483647")
    config["trigger_guid_base"] = base
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(config.get("version", "0.1.0"))):
        warn("version is best written as three numbers, for example 1.0.0")
    if config.get("schema_version", 1) != 1:
        raise ToolError("this version of generate.py understands config schema_version 1")
    if any(character.isspace() for character in str(config["mod_id"])):
        warn("mod_id contains whitespace; the loader works best with a simple ID")
    if not str(config["script_prefix"]).replace("_", "").isalnum():
        warn("script_prefix is best kept to letters, numbers and underscores")
    if not config["modules"]:
        raise ToolError("config has no modules")
    if int(config["trigger_guid_base"]) in (900000100, 900000500):
        warn(
            "trigger_guid_base is the example placeholder; choose a free band "
            "in your own GUID range before publishing"
        )


def build(config: dict, config_path: Path, out_dir: Path, preset: dict, preset_path: Path, compat: dict | None, dry_run: bool) -> dict:
    validate_config(config)
    templates = load_templates()
    hide = config["hide_session"]
    shows = resolve_show_sessions(config, hide)
    next_guid = int(config["trigger_guid_base"])
    script_prefix = config["script_prefix"]
    marker_dir = config.get("marker_dir", "logs")
    creative_enabled = bool(config.get("creative_restore", True))
    triggers_enabled = bool(config.get("generate_triggers", True))
    streets_config = config.get("streets_unified", {})
    streets_required = bool(streets_config.get("required", True))

    modules: list[dict] = []
    for module in config["modules"]:
        if not module.get("enabled", True):
            continue
        module = dict(module)
        if module.get("key") == "compat" and compat is not None:
            module["items"] = module.get("items", [])
        items = collect_module_items(module, config_path.parent, preset, compat)
        if not items:
            warn(f"module {module.get('key')} has no items and was skipped")
            continue
        modules.append(
            {
                "key": module["key"],
                "name": module.get("name", module["key"]),
                "items": items,
                "keep_unlocked": sorted(
                    set(guid_list(module.get("keep_unlocked", preset_street_guids(preset)), "keep_unlocked")),
                    key=int,
                ),
                "creative": bool(module.get("creative_restore", creative_enabled)),
            }
        )
    if not modules:
        raise ToolError("no module produced any items; nothing to generate")

    all_item_guids = {guid for module in modules for guid in module["items"]}
    used_trigger_guids: set[str] = set()
    for module in modules:
        count = 1 + len(shows) * (2 if module["creative"] else 1)
        module["hide_guid"] = str(next_guid)
        next_guid += 1
        module["show_guids"] = [str(next_guid + index) for index in range(len(shows))]
        next_guid += len(shows)
        module["creative_guids"] = []
        if module["creative"]:
            module["creative_guids"] = [str(next_guid + index) for index in range(len(shows))]
            next_guid += len(shows)
        module["trigger_guids"] = (
            [module["hide_guid"]] + module["show_guids"] + module["creative_guids"]
        )
        for guid in module["trigger_guids"]:
            if guid in used_trigger_guids:
                raise ToolError(f"trigger GUID {guid} was allocated twice")
            if guid in all_item_guids:
                raise ToolError(f"trigger GUID {guid} is also an item GUID; move trigger_guid_base")
            used_trigger_guids.add(guid)
        module["trigger_count"] = count

    if next_guid - 1 > 2147483647:
        raise ToolError("the trigger GUID range exceeds the int32 limit; move trigger_guid_base lower")

    if dry_run:
        return {
            "out_dir": out_dir,
            "modules": modules,
            "shows": shows,
            "trigger_guid_end": str(next_guid - 1),
            "triggers_enabled": triggers_enabled,
        }

    trigger_parts: list[str] = []
    for module in modules:
        items_lua = lua_values(module["items"])
        always_lua = lua_values(module["keep_unlocked"])
        marker = f"{marker_dir}/{script_prefix}_{module['key']}.restore"
        context = {
            "toolkit_version": __version__,
            "module_name": module["name"],
            "count": str(len(module["items"])),
            "session_name": hide.get("name", hide["guid"]),
            "session_guid": as_guid(hide["guid"], "hide session GUID"),
            "items": items_lua,
            "always": always_lua,
            "marker": marker,
        }
        write_text(
            out_dir / "data/script" / f"{script_prefix}_{module['key']}_hide.lua",
            templates["hide"].substitute(context),
        )
        write_text(
            out_dir / "data/script" / f"{script_prefix}_{module['key']}_show.lua",
            templates["show"].substitute(context),
        )
        if module["creative"]:
            write_text(
                out_dir / "data/script" / f"{script_prefix}_{module['key']}_creative.lua",
                templates["creative"].substitute(context),
            )

        def trigger(guid: str, name: str, session: dict, script: str, subs: str) -> str:
            return templates["trigger"].substitute(
                {
                    "guid": guid,
                    "name": name,
                    "session": as_guid(session["guid"]),
                    "script": script,
                    "subs": subs,
                }
            )

        trigger_parts.append(
            trigger(
                module["hide_guid"],
                f"Hide {module['name']} in {hide.get('name', hide['guid'])}",
                hide,
                f"{script_prefix}_{module['key']}_hide.lua",
                "",
            )
        )
        for session, guid in zip(shows, module["show_guids"]):
            trigger_parts.append(
                trigger(
                    guid,
                    f"Restore {module['name']} in {session['name']}",
                    session,
                    f"{script_prefix}_{module['key']}_show.lua",
                    templates["sub_not_creative"].substitute({}),
                )
            )
        if module["creative"]:
            for session, guid in zip(shows, module["creative_guids"]):
                trigger_parts.append(
                    trigger(
                        guid,
                        f"Restore {module['name']} in creative ({session['name']})",
                        session,
                        f"{script_prefix}_{module['key']}_creative.lua",
                        templates["sub_creative"].substitute({}),
                    )
                )

    dependencies = ["Streets_Unified"] if streets_required else []
    dependencies.extend(config.get("dependencies", []))
    dependencies = list(dict.fromkeys(dependencies))
    modinfo = {
        "Version": str(config.get("version", "0.1.0")),
        "ModID": config["mod_id"],
        "Category": localized(config.get("category", "Gameplay")),
        "ModName": localized(config["mod_name"]),
        "Description": localized(config.get("description", "")),
        "KnownIssues": config.get("known_issues", []),
        "CreatorName": config.get("creator", ""),
    }
    if dependencies:
        modinfo["ModDependencies"] = dependencies
        modinfo["LoadAfterIds"] = list(dependencies)
    write_json(out_dir / "modinfo.json", modinfo)

    trigger_records: list[dict] = []
    for module in modules:
        trigger_records.append(
            {
                "kind": "hide",
                "guid": module["hide_guid"],
                "name": f"Hide {module['name']} in {hide.get('name', hide['guid'])}",
                "session": as_guid(hide["guid"]),
                "session_name": hide.get("name", ""),
                "script": f"{script_prefix}_{module['key']}_hide.lua",
                "creative": False,
            }
        )
        for session, guid in zip(shows, module["show_guids"]):
            trigger_records.append(
                {
                    "kind": "show",
                    "guid": guid,
                    "name": f"Restore {module['name']} in {session['name']}",
                    "session": as_guid(session["guid"]),
                    "session_name": session.get("name", ""),
                    "script": f"{script_prefix}_{module['key']}_show.lua",
                    "creative": False,
                }
            )
        for session, guid in zip(shows, module["creative_guids"]):
            trigger_records.append(
                {
                    "kind": "creative",
                    "guid": guid,
                    "name": f"Restore {module['name']} in creative ({session['name']})",
                    "session": as_guid(session["guid"]),
                    "session_name": session.get("name", ""),
                    "script": f"{script_prefix}_{module['key']}_creative.lua",
                    "creative": True,
                }
            )

    assets_header = (
        "<ModOps>\n"
        f"    <!-- Generated by {TOOLKIT_NAME} {__version__}. Do not edit by hand. -->\n"
        f"    <!-- Region: {preset['display_name']} ({preset['region_node']}). "
        f"Hide session: {hide.get('name', hide['guid'])} ({as_guid(hide['guid'])}). -->\n"
    )
    assets_path = out_dir / "data/config/export/main/asset/assets.xml"
    manifest_json = out_dir / "menugate.triggers.json"
    manifest_text = out_dir / "menugate.triggers.xml.txt"
    if triggers_enabled:
        write_text(assets_path, assets_header + "".join(trigger_parts) + "</ModOps>\n")
        for stale in (manifest_json, manifest_text):
            if stale.exists():
                stale.unlink()
    else:
        if assets_path.exists():
            assets_path.unlink()
        write_json(
            manifest_json,
            {
                "schema_version": 1,
                "generated_by": f"{TOOLKIT_NAME} {__version__}",
                "region": preset["key"],
                "region_node": preset["region_node"],
                "note": (
                    "Triggers were skipped. Add these to your own assets.xml, or copy "
                    "the snippet in menugate.triggers.xml.txt."
                ),
                "triggers": trigger_records,
            },
        )
        manual_header = (
            "<ModOps>\n"
            f"    <!-- Generated by {TOOLKIT_NAME} {__version__}. Triggers were skipped. -->\n"
            f"    <!-- Region: {preset['display_name']} ({preset['region_node']}). "
            f"Hide session: {hide.get('name', hide['guid'])} ({as_guid(hide['guid'])}). -->\n"
        )
        write_text(manifest_text, manual_header + "".join(trigger_parts) + "</ModOps>\n")

    provenance = {
        "schema_version": 1,
        "toolkit": TOOLKIT_NAME,
        "toolkit_version": __version__,
        "region": preset["key"],
        "region_node": preset["region_node"],
        "preset": preset_path.name,
        "hide_session": {"guid": as_guid(hide["guid"]), "name": hide.get("name", "")},
        "show_sessions": shows,
        "streets_unified_required": streets_required,
        "triggers_generated": triggers_enabled,
        "trigger_count": len(trigger_records),
        "modules": [
            {
                "key": module["key"],
                "name": module["name"],
                "items": len(module["items"]),
                "hide_trigger": module["hide_guid"],
                "show_triggers": module["show_guids"],
                "creative_triggers": module["creative_guids"],
            }
            for module in modules
        ],
        "trigger_guid_end": str(next_guid - 1),
        "config": config,
    }
    canonical = json.dumps(provenance, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    provenance["config_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    write_json(out_dir / "menugate.config.json", provenance)
    return {
        "out_dir": out_dir,
        "modules": modules,
        "shows": shows,
        "trigger_guid_end": str(next_guid - 1),
        "triggers_enabled": triggers_enabled,
    }


def load_compat(path: Path | None) -> dict | None:
    if path is None:
        return None
    data = read_json(path)
    if not isinstance(data, dict):
        raise ToolError(f"compat file is not an object: {path}")
    if not isinstance(data.get("items", []), list):
        raise ToolError(f"compat file has no items list: {path}")
    return data


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True, help="Path to the gate config JSON")
    parser.add_argument("--preset", help="Region preset key or path (default: the config's region)")
    parser.add_argument("--compat", help="Compatibility list from scan_mods.py")
    parser.add_argument("--guid-base", help="First trigger GUID, overriding the config value")
    parser.add_argument(
        "--skip-triggers",
        action="store_true",
        help="Write the Lua and modinfo but not the trigger XML; write a manifest instead",
    )
    parser.add_argument("--out", help="Output folder (default: the config's output, or out/<mod_id>)")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without writing files")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config).resolve()
    try:
        config = read_json(config_path)
        if not isinstance(config, dict):
            raise ToolError(f"config is not an object: {config_path}")
        if args.guid_base is not None:
            config["trigger_guid_base"] = args.guid_base
        if args.skip_triggers:
            config["generate_triggers"] = False
        preset_name = args.preset or config.get("region")
        if not preset_name:
            raise ToolError("config has no region and --preset was not given")
        preset, preset_path = load_preset(preset_name)
        compat = load_compat(Path(args.compat) if args.compat else None)
        if compat is not None and not any(module.get("key") == "compat" for module in config.get("modules", [])):
            config.setdefault("modules", []).append(
                {
                    "key": "compat",
                    "name": "Installed mods",
                    "enabled": True,
                    "items": [],
                }
            )
        out_dir = Path(args.out) if args.out else config_path.parent / config.get("output", f"out/{config['mod_id']}")
        result = build(config, config_path, out_dir.resolve(), preset, preset_path, compat, args.dry_run)
    except FileNotFoundError as error:
        fail(f"file not found: {error.filename}")
    except ToolError as error:
        fail(str(error))

    info(f"region: {preset['display_name']} ({preset['region_node']})")
    for module in result["modules"]:
        info(
            f"  {module['key']}: {len(module['items'])} items, "
            f"hide {module['hide_guid']}, "
            f"{len(module['show_guids'])} restore triggers"
            + (f", {len(module['creative_guids'])} creative triggers" if module["creative"] else "")
        )
    info(f"trigger GUIDs end at {result['trigger_guid_end']}")
    if result.get("triggers_enabled", True):
        info("triggers: written to assets.xml")
    else:
        info("triggers: skipped; see menugate.triggers.json and menugate.triggers.xml.txt")
    if args.dry_run:
        info(f"dry run: would write {result['out_dir']}")
    else:
        info(f"wrote {result['out_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
