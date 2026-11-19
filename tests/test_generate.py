import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import generate


def config() -> dict:
    return {
        "schema_version": 1,
        "mod_id": "TestGate",
        "mod_name": "Test Gate",
        "creator": "Fixture",
        "version": "0.1.0",
        "description": "Test only",
        "category": "Gameplay",
        "region": "new_world",
        "hide_session": {"guid": 900000001, "name": "Test Session"},
        "trigger_guid_base": 1900000100,
        "script_prefix": "test_gate",
        "marker_dir": "logs",
        "modules": [
            {
                "key": "core",
                "name": "Base game",
                "items": [101257, 101254, 101308],
            }
        ],
    }


def write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def files_in(path: Path) -> dict[str, bytes]:
    return {
        str(item.relative_to(path)): item.read_bytes()
        for item in path.rglob("*")
        if item.is_file()
    }


def find_luac() -> str | None:
    for name in ("luac", "luac5.4", "luac5.3", "luac5.2"):
        path = shutil.which(name)
        if path:
            return path
    return None


def test_generate_writes_a_complete_mod(tmp_path: Path) -> None:
    cfg = write_config(tmp_path, config())
    out = tmp_path / "out"
    assert generate.main(["--config", str(cfg), "--out", str(out)]) == 0

    modinfo = json.loads((out / "modinfo.json").read_text(encoding="utf-8"))
    assert modinfo["ModID"] == "TestGate"
    assert modinfo["ModDependencies"] == ["Streets_Unified"]
    assert modinfo["LoadAfterIds"] == ["Streets_Unified"]
    assert set(modinfo["ModName"]) == set(generate.LANGUAGES)
    assert modinfo["ModName"]["English"] == "Test Gate"
    assert modinfo["ModName"]["German"] is None

    tree = ET.parse(out / "data/config/export/main/asset/assets.xml")
    assert len(tree.getroot().findall("ModOp")) == 16

    hide = (out / "data/script/test_gate_core_hide.lua").read_text(encoding="utf-8")
    assert "101254" in hide and "101257" in hide
    assert "101308" in hide  # kept unlocked, not in the lock list

    luac = find_luac()
    for name in ("hide", "show", "creative"):
        path = out / "data/script" / f"test_gate_core_{name}.lua"
        assert path.exists()
        if luac:
            subprocess.run([luac, "-p", str(path)], check=True)


def test_generate_is_deterministic(tmp_path: Path) -> None:
    cfg = write_config(tmp_path, config())
    first = tmp_path / "first"
    second = tmp_path / "second"
    assert generate.main(["--config", str(cfg), "--out", str(first)]) == 0
    assert generate.main(["--config", str(cfg), "--out", str(second)]) == 0
    assert files_in(first) == files_in(second)


def test_compat_file_adds_a_second_module(tmp_path: Path) -> None:
    cfg = write_config(tmp_path, config())
    compat = tmp_path / "compat.json"
    compat.write_text(json.dumps({"items": [{"guid": 9009, "source_mod": "Fixture"}]}), encoding="utf-8")
    out = tmp_path / "out"
    assert generate.main(["--config", str(cfg), "--compat", str(compat), "--out", str(out)]) == 0
    assert (out / "data/script/test_gate_compat_hide.lua").exists()
    tree = ET.parse(out / "data/config/export/main/asset/assets.xml")
    assert len(tree.getroot().findall("ModOp")) == 32


def test_skip_triggers_writes_a_manual_manifest(tmp_path: Path) -> None:
    cfg = write_config(tmp_path, config())
    out = tmp_path / "out"
    assert generate.main(["--config", str(cfg), "--out", str(out), "--skip-triggers"]) == 0
    assert not (out / "data/config/export/main/asset/assets.xml").exists()
    assert (out / "data/script/test_gate_core_hide.lua").exists()
    manifest = json.loads((out / "menugate.triggers.json").read_text(encoding="utf-8"))
    assert len(manifest["triggers"]) == 16
    text = (out / "menugate.triggers.xml.txt").read_text(encoding="utf-8")
    assert text.count("<ModOp ") == 16
    ET.fromstring(text)
    provenance = json.loads((out / "menugate.config.json").read_text(encoding="utf-8"))
    assert provenance["triggers_generated"] is False
    assert provenance["trigger_count"] == 16


def test_config_can_skip_triggers(tmp_path: Path) -> None:
    data = config()
    data["generate_triggers"] = False
    cfg = write_config(tmp_path, data)
    out = tmp_path / "out"
    assert generate.main(["--config", str(cfg), "--out", str(out)]) == 0
    assert (out / "menugate.triggers.json").exists()
    assert not (out / "data/config/export/main/asset/assets.xml").exists()


def test_enabling_triggers_removes_a_stale_manifest(tmp_path: Path) -> None:
    data = config()
    data["generate_triggers"] = False
    cfg = write_config(tmp_path, data)
    out = tmp_path / "out"
    assert generate.main(["--config", str(cfg), "--out", str(out)]) == 0
    data["generate_triggers"] = True
    cfg.write_text(json.dumps(data), encoding="utf-8")
    assert generate.main(["--config", str(cfg), "--out", str(out)]) == 0
    assert (out / "data/config/export/main/asset/assets.xml").exists()
    assert not (out / "menugate.triggers.json").exists()


def test_empty_trigger_base_is_rejected(tmp_path: Path) -> None:
    data = config()
    data["trigger_guid_base"] = None
    cfg = write_config(tmp_path, data)
    preset, preset_path = generate.load_preset("new_world")
    with pytest.raises(generate.ToolError):
        generate.build(data, cfg, tmp_path / "out", preset, preset_path, None, False)


def test_guid_range_overflow_is_rejected(tmp_path: Path) -> None:
    data = config()
    data["trigger_guid_base"] = 2147483647
    cfg = write_config(tmp_path, data)
    preset, preset_path = generate.load_preset("new_world")
    with pytest.raises(generate.ToolError):
        generate.build(data, cfg, tmp_path / "out", preset, preset_path, None, False)


def test_hide_session_cannot_be_a_show_session() -> None:
    data = config()
    data["show_sessions"] = [{"guid": 900000001, "name": "Test Session"}]
    with pytest.raises(generate.ToolError):
        generate.resolve_show_sessions(data, data["hide_session"])


def test_trigger_guid_cannot_collide_with_an_item(tmp_path: Path) -> None:
    data = config()
    data["trigger_guid_base"] = 101257
    cfg = write_config(tmp_path, data)
    with pytest.raises(generate.ToolError):
        generate.build(
            data,
            cfg,
            tmp_path / "out",
            generate.load_preset("new_world")[0],
            Path("new_world.json"),
            None,
            False,
        )


def test_generated_engine_has_generic_settle_and_logging(tmp_path: Path) -> None:
    cfg = write_config(tmp_path, config())
    out = tmp_path / "out"
    assert generate.main(["--config", str(cfg), "--out", str(out)]) == 0

    tree = ET.parse(out / "data/config/export/main/asset/assets.xml")
    ops = tree.getroot().findall("ModOp")

    def values(op):
        return op.find("Asset/Values")

    # Generic restore: ConditionActiveSession + SessionBlacklist 1, plus a
    # delayed ActionUnlockAsset on the settle flag.
    generic = [
        op for op in ops
        if values(op).find("Trigger/TriggerCondition/Template") is not None
        and values(op).findtext("Trigger/TriggerCondition/Template") == "ConditionActiveSession"
        and values(op).findtext("Trigger/TriggerCondition/Values/ConditionActiveSession/SessionBlacklist") == "1"
    ]
    assert len(generic) == 2  # normal and creative
    delayed = generic[0].find(".//ActionDelayedActions")
    assert delayed is not None
    assert delayed.findtext("ExecutionDelay") == "500"
    assert delayed.findtext(".//ActionUnlockAsset/UnlockAssets/Item/Asset")

    # Settle: ConditionUnlocked on the flag, with the hidden-session guard.
    settle = [op for op in ops if values(op).findtext("Trigger/TriggerCondition/Template") == "ConditionUnlocked"]
    assert len(settle) == 2
    for op in settle:
        assert op.findtext(".//ActionLockAsset/LockAssets/Item/Asset") == values(op).findtext(
            "Trigger/TriggerCondition/Values/ConditionUnlocked/UnlockNeeded"
        )
        assert op.findtext(".//SubTriggers//ConditionActiveSession/SessionBlacklist") == "1"
        assert op.findtext(".//SubTriggers//TriggerCondition/Template") == "ConditionIsCreativeMode"
    # Normal settle is negated creative; the second settle is positive creative.
    assert settle[0].findtext(".//NegateCondition") == "1"
    assert settle[1].findtext(".//NegateCondition") is None

    # Marker v2, the lookup-failure rule and the log block live in the scripts.
    show = (out / "data/script/test_gate_core_show.lua").read_text(encoding="utf-8")
    for needle in ("v2|", "marker_valid(MARKER, SIG, MARKER_AGE)", "if not qok then", "reg_ok[tt] == true", "gate_log("):
        assert needle in show
    for name in ("hide", "show", "creative"):
        script = (out / "data/script" / f"test_gate_core_{name}.lua").read_text(encoding="utf-8")
        assert "logs/menugate_debug.off" in script
        assert "pcall(function() return os.time() end)" in script


def test_creative_off_gates_the_hide_to_non_creative(tmp_path: Path) -> None:
    data = config()
    data["creative_restore"] = False
    cfg = write_config(tmp_path, data)
    out = tmp_path / "out"
    assert generate.main(["--config", str(cfg), "--out", str(out)]) == 0
    assert not (out / "data/script/test_gate_core_creative.lua").exists()
    tree = ET.parse(out / "data/config/export/main/asset/assets.xml")
    assert len(tree.getroot().findall("ModOp")) == 9
    hide = tree.getroot().findall("ModOp")[0]
    assert hide.find(".//ConditionIsCreativeMode") is not None
    assert hide.findtext(".//NegateCondition") == "1"
