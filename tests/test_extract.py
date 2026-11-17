from pathlib import Path

import pytest

import extract_tier_menu
from common import ToolError


ASSETS = """<Assets>
  <Asset>
    <Template>ConstructionCategory</Template>
    <Values>
      <Standard><GUID>900</GUID><Name>Test Tab</Name></Standard>
      <ConstructionCategory><BuildingList>
        <Item><Category>901</Category></Item>
        <Item><Building>902</Building></Item>
      </BuildingList></ConstructionCategory>
    </Values>
  </Asset>
  <Asset>
    <Template>ConstructionCategory</Template>
    <Values>
      <Standard><GUID>901</GUID><Name>Nested Menu</Name></Standard>
      <ConstructionCategory><BuildingList>
        <Item><Building>903</Building></Item>
      </BuildingList></ConstructionCategory>
    </Values>
  </Asset>
</Assets>
"""


def preset() -> dict:
    return {
        "schema_version": 1,
        "key": "test",
        "display_name": "Test",
        "menu_guid": 25000035,
        "region_node": "Test",
        "host_sessions": [],
        "related_sessions": [],
        "tier_tabs": [{"guid": 900, "name": "Test Tab"}],
        "street_assets": [],
        "tested_in_game": False,
    }


def test_extract_counts_leaves_containers_and_tabs(tmp_path: Path) -> None:
    assets = tmp_path / "assets.xml"
    assets.write_text(ASSETS, encoding="utf-8")
    result = extract_tier_menu.build(assets, preset())
    assert result["leaves"] == ["902", "903"]
    assert result["containers"] == ["901"]
    assert result["totals"] == {"tabs": 1, "leaves": 2, "containers": 1, "locked_items": 4}
    assert result["tabs"][0]["name"] == "Test Tab"


def test_extract_rejects_a_missing_tab(tmp_path: Path) -> None:
    assets = tmp_path / "assets.xml"
    assets.write_text(ASSETS, encoding="utf-8")
    bad = preset()
    bad["tier_tabs"] = [{"guid": 999, "name": "Missing"}]
    with pytest.raises(ToolError):
        extract_tier_menu.build(assets, bad)
