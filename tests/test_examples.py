import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def example_configs() -> list[tuple[str, dict]]:
    result = []
    for path in sorted((ROOT / "examples").glob("*/config.json")):
        result.append((path.parent.name, json.loads(path.read_text(encoding="utf-8"))))
    return result


def test_examples_leave_the_trigger_guid_base_empty() -> None:
    for name, config in example_configs():
        assert config["trigger_guid_base"] is None, name


def test_example_session_guids_are_distinct() -> None:
    guids = {}
    for name, config in example_configs():
        if name == "demo_new_world":
            continue
        guid = config["hide_session"]["guid"]
        assert guid not in guids, f"{name} and {guids[guid]} share {guid}"
        guids[guid] = name
    assert len(guids) == 4
