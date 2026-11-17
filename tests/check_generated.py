"""Check generated example mods.

Run this after generating the examples in CI or before a release. It parses
every generated XML file, checks the modinfo dependency, and runs the Lua syntax
checker when one is installed.

Usage:
  python tests/check_generated.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"


def find_luac() -> str | None:
    for name in ("luac", "luac5.4", "luac5.3", "luac5.2"):
        path = shutil.which(name)
        if path:
            return path
    return None


def main() -> int:
    xml_files = [path for path in EXAMPLES.rglob("assets.xml") if "out" in path.parts]
    lua_files = [path for path in EXAMPLES.rglob("*.lua") if "out" in path.parts]
    modinfo_files = [path for path in EXAMPLES.rglob("modinfo.json") if "out" in path.parts]
    if not xml_files or not lua_files or not modinfo_files:
        print("error: no generated example mods found; run the generator first", file=sys.stderr)
        return 1

    for path in xml_files:
        ET.parse(path)

    for path in modinfo_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        dependencies = data.get("ModDependencies", [])
        if "Streets_Unified" not in dependencies:
            print(f"error: {path} does not depend on Streets_Unified", file=sys.stderr)
            return 1

    luac = find_luac()
    if luac:
        for path in lua_files:
            subprocess.run([luac, "-p", str(path)], check=True)
        lua_note = f"{len(lua_files)} Lua files"
    else:
        lua_note = f"{len(lua_files)} Lua files (no luac found, syntax check skipped)"

    print(f"checked {len(xml_files)} XML files, {lua_note}, {len(modinfo_files)} modinfo files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
