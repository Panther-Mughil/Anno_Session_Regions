import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPANION = ROOT / "companions/streets_unified"
CATEGORIES = {"2001229950", "2001229951", "2001229952", "2001229953"}


def test_modinfo_has_all_languages_and_alpha_version() -> None:
    data = json.loads((COMPANION / "modinfo.json").read_text(encoding="utf-8"))
    assert data["Version"] == "0.1.0"
    assert data["ModID"] == "Streets_Unified"
    for field in ("Category", "ModName", "Description"):
        assert len(data[field]) == 11
        assert data[field]["English"]


def test_categories_have_text_and_locked_blocks() -> None:
    tree = ET.parse(COMPANION / "data/config/export/main/asset/assets.xml")
    assets = {}
    for asset in tree.getroot().iter("Asset"):
        guid = asset.findtext("Values/Standard/GUID")
        if guid:
            assets[guid] = asset
    for guid in CATEGORIES:
        values = assets[guid].find("Values")
        tags = [child.tag for child in values]
        assert "Text" in tags and "Locked" in tags


def test_texts_cover_all_languages_and_categories() -> None:
    files = sorted((COMPANION / "data/config/gui").glob("texts_*.xml"))
    assert len(files) == 11
    for path in files:
        tree = ET.parse(path)
        guids = {node.findtext("GUID") for node in tree.iter("Text")}
        assert CATEGORIES <= guids, path.name
