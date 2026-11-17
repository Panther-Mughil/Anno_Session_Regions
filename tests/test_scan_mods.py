import argparse
import json
from pathlib import Path

import scan_mods


def write_mod(root: Path, folder: str, mod_id: str, version: str, assets_xml: str) -> Path:
    path = root / folder
    path.mkdir(parents=True, exist_ok=True)
    (path / "modinfo.json").write_text(
        json.dumps(
            {
                "ModID": mod_id,
                "Version": version,
                "ModName": {"English": folder},
                "CreatorName": "Fixture",
            }
        ),
        encoding="utf-8",
    )
    (path / "assets.xml").write_text(assets_xml, encoding="utf-8")
    return path


def args_for(root: Path, *extra_roots: Path, include_disabled: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        preset="new_world",
        assets=None,
        game_dir=None,
        mods_root=[str(root)] + [str(path) for path in extra_roots],
        documents=None,
        modio=None,
        no_autodetect=True,
        include_disabled=include_disabled,
        out=None,
        print_roots=False,
        strict=False,
        quiet=True,
    )


def doc(*fragments: str) -> str:
    return "<ModOps>\n" + "\n".join(fragments) + "\n</ModOps>\n"


def add_to_tab(tab: int, building: int) -> str:
    return f"""<ModOp Type="addNextSibling" GUID="{tab}" Path="Values/ConstructionCategory/BuildingList">
    <Item><Building>{building}</Building></Item>
  </ModOp>"""


def define_category(guid: str, name: str, children: list[int]) -> str:
    items = "".join(f"<Item><Building>{child}</Building></Item>" for child in children)
    return f"""<ModOp Type="addNextSibling" GUID="130248">
    <Asset>
      <Template>ConstructionCategory</Template>
      <Values>
        <Standard><GUID>{guid}</GUID><Name>{name}</Name></Standard>
        <ConstructionCategory><BuildingList>{items}</BuildingList></ConstructionCategory>
      </Values>
    </Asset>
  </ModOp>"""


def test_scanner_finds_mod_items_and_new_tabs(tmp_path: Path) -> None:
    root1 = tmp_path / "root1"
    root2 = tmp_path / "root2"
    root1.mkdir()
    root2.mkdir()
    (root1 / "activations.json").write_text(json.dumps({"disabledIds": ["DisabledMod"]}), encoding="utf-8")

    write_mod(root1, "ModA", "ModA", "1.0", doc(add_to_tab(25000193, 9001)))
    write_mod(root2, "ModA", "ModA", "2.0", doc(add_to_tab(25000193, 9002)))
    write_mod(root1, "Disabled", "DisabledMod", "1.0", doc(add_to_tab(25000193, 9004)))

    new_tab = """<ModOp Type="addPrevSibling" GUID="25000035"
         Path="/Values/ConstructionMenu/RegionMenu/Colony01/CategoryMode/Tier/Categories/Item[Category='25000194']">
      <Item><Category>8000</Category></Item>
    </ModOp>"""
    write_mod(root1, "NewTab", "NewTab", "1.0", doc(new_tab, define_category("8000", "Mod Menu", [9003])))

    inside = """<ModOp Type="addNextSibling" GUID="25000194" Path="Values/ConstructionCategory/BuildingList">
      <Item><Category>8001</Category></Item>
    </ModOp>"""
    write_mod(root1, "Inside", "Inside", "1.0", doc(inside, define_category("8001", "Inside Menu", [9005, 9006])))

    nested = """<ModOp Type="add" GUID="7425" Path="Values/ConstructionCategory/BuildingList">
      <Item><Building>9007</Building></Item>
    </ModOp>"""
    write_mod(root1, "Nested", "Nested", "1.0", doc(nested))

    remover = """<ModOp Type="remove" GUID="25000194"
         Path="Values/ConstructionCategory/BuildingList/Item[Building='101257']" />"""
    write_mod(root1, "Remover", "Remover", "1.0", doc(remover))

    result = scan_mods.build(args_for(root1, root2))
    items = {entry["guid"] for entry in result["items"]}
    assert items == {8001, 9002, 9005, 9006, 9007}
    assert {entry["guid"] for entry in result["new_tabs"]} == {8000}
    assert {entry["guid"] for entry in result["removed"]} == {101257}
    assert any("version 2.0" in warning for warning in result["warnings"])
    disabled = [mod for mod in result["mods"] if mod["mod_id"] == "DisabledMod"]
    assert disabled and disabled[0]["enabled"] is False

    result_with_disabled = scan_mods.build(args_for(root1, root2, include_disabled=True))
    assert 9004 in {entry["guid"] for entry in result_with_disabled["items"]}


def test_scanner_finds_roots(tmp_path: Path) -> None:
    root = tmp_path / "mods"
    root.mkdir()
    write_mod(root, "One", "One", "1.0", doc(add_to_tab(25000193, 9100)))
    args = args_for(root)
    found, missing = scan_mods.resolve_roots(args)
    assert found == [root]
    assert missing == []
