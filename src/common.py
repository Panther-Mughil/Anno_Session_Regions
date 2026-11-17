"""Shared helpers for the Anno Session Regions tools."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from version import __version__

REPO_ROOT = Path(__file__).resolve().parent.parent
PRESETS_DIR = REPO_ROOT / "presets"
ITEMS_DIR = PRESETS_DIR / "items"
TEMPLATES_DIR = REPO_ROOT / "templates"

PRESET_REQUIRED = (
    "schema_version",
    "key",
    "display_name",
    "menu_guid",
    "region_node",
    "tier_tabs",
    "street_assets",
)


class ToolError(Exception):
    """A problem the user can fix, such as a missing file or a bad value."""


def fail(message: str, code: int = 2) -> "None":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def info(message: str) -> None:
    print(message)


def read_json(path: Path) -> object:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: object) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def as_guid(value: object, label: str = "GUID") -> str:
    """Return a GUID as a plain decimal string, or raise a readable error."""
    text = str(value).strip()
    if not text.isdigit():
        raise ToolError(f"{label} must be a number, got {value!r}")
    return str(int(text))


def guid_list(values: object, label: str = "GUID list") -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ToolError(f"{label} must be a list")
    return [as_guid(value, label) for value in values]


def version_key(text: str) -> tuple[int, ...]:
    """Turn a mod version into a sortable key. Text after the numbers is ignored."""
    parts = re.findall(r"\d+", str(text))
    if not parts:
        return (0,)
    return tuple(int(part) for part in parts)


def load_preset(name_or_path: str | Path) -> tuple[dict, Path]:
    """Load a preset by key or path and check the fields the tools rely on."""
    path = Path(name_or_path)
    if not path.exists():
        path = PRESETS_DIR / f"{name_or_path}.json"
    if not path.exists():
        raise ToolError(f"preset not found: {name_or_path}")
    data = read_json(path)
    if not isinstance(data, dict):
        raise ToolError(f"preset is not an object: {path}")
    missing = [key for key in PRESET_REQUIRED if key not in data]
    if missing:
        raise ToolError(f"preset {path} is missing: {', '.join(missing)}")
    if data["schema_version"] != 1:
        raise ToolError(
            f"preset {path} uses schema_version {data['schema_version']}, "
            "this version of the tools understands 1"
        )
    if not data["tier_tabs"]:
        raise ToolError(f"preset {path} has no tier_tabs")
    return data, path


def load_sessions() -> list[dict]:
    path = PRESETS_DIR / "sessions.json"
    if not path.exists():
        raise ToolError(f"session list not found: {path}")
    data = read_json(path)
    return data["sessions"]


def preset_tab_guids(preset: dict) -> list[str]:
    return [as_guid(tab["guid"], "tier tab GUID") for tab in preset["tier_tabs"]]


def preset_street_guids(preset: dict) -> list[str]:
    return guid_list(preset.get("street_assets", []), "street asset GUID")


def read_item_file(path: Path) -> dict:
    data = read_json(path)
    if not isinstance(data, dict):
        raise ToolError(f"item file is not an object: {path}")
    return data
