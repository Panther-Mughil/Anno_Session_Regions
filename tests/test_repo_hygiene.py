import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {".md", ".py", ".json", ".xml", ".lua", ".yml", ".yaml", ".txt", ".toml"}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "out", ".venv", "companions"}
PRIVATE_TERMS = ("Land of Harvests", "Marudia", "Bountiful", "Anno-Forge", "SessionMenuGate")


def text_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        files.append(path)
    return files


def test_version_is_an_alpha_prerelease() -> None:
    text = (ROOT / "src/version.py").read_text(encoding="utf-8")
    match = re.search(r'__version__ = "([^"]+)"', text)
    assert match
    assert re.fullmatch(r"\d+\.\d+\.\d+-alpha\.\d+", match.group(1))


def test_no_developer_paths_in_shipped_code() -> None:
    offenders = []
    for path in text_files():
        relative = path.relative_to(ROOT)
        if relative.parts[0] in {"docs", "tests"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "/mnt/" in text or "/home/" in text or "C:\\" in text:
            offenders.append(str(relative))
    assert offenders == []


def test_no_private_mod_content_in_the_public_repo() -> None:
    offenders = []
    for path in text_files():
        if path.name == "test_repo_hygiene.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for term in PRIVATE_TERMS:
            if term.lower() in text.lower():
                offenders.append(f"{path.relative_to(ROOT)}: {term}")
    assert offenders == []
