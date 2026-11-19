# Development

## Layout

```
src/            the four command line tools and shared helpers
                (generate.py also holds the emitted Lua and XML shapes)
presets/        one JSON file per host region, plus generated item lists
examples/       a config per region and a New World demo
companions/     Streets Unified, shipped as a separate mod
tests/          pytest suite and fixture data
docs/           the guide
```

The generator emits its Lua and XML from string constants in `src/generate.py`, not from separate template files. That keeps the engine in one place: the log block, the restore loop, the marker format, the trigger shapes and the GUID allocation cannot drift from each other.

## Setup

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

The tools themselves need only the Python standard library. pytest is for development.

Lua syntax checks use `luac`. On Debian and Ubuntu:

```sh
sudo apt install lua5.4
```

The tests skip the Lua check when `luac` is not on the path. CI installs Lua so the check always runs there.

## Tests

The suite covers:

- `test_extract.py`: the extractor with a small vanilla-like fixture.
- `test_generate.py`: a complete generated mod, deterministic output, compatibility modules, GUID collision checks, Lua syntax, and the engine invariants (generic restore + 500 ms cue, settle flag, marker v2, the failed-lookup rule, and creative-off gating).
- `test_presets.py`: the four shipped presets and item lists against expected counts.
- `test_scan_mods.py`: fixture mods, duplicate ModIDs, disabled mods, new tabs, nested categories, and removals.
- `test_repo_hygiene.py`: version format, no developer paths in shipped code, no private project names in the public repository.
- `test_companion.py`: the Streets Unified categories, the 11 text files, and the 11-key modinfo.
- `test_examples.py`: the examples leave the trigger base empty, use distinct placeholder session GUIDs, and point at their own region item list.
- Manual trigger mode is covered in `test_generate.py`: no `assets.xml`, a JSON manifest, and a copy-ready XML snippet.

The tests do not need a game install. Keep them that way so CI can run anywhere.

## Regenerating the item lists

```sh
python src/extract_tier_menu.py --assets "/path/to/assets.xml" \
  --preset presets/new_world.json \
  --out presets/items/new_world_core.json
```

Do this after a game update changes the menu. The tests compare the shipped counts with the presets, so a change is visible.

## Drafting presets after a game update

```sh
python src/discover_regions.py --assets "/path/to/assets.xml" --out-dir presets/drafts
```

The tool reads every `RegionMenu` node, lists the tier tabs, and counts their contents. It fills the known host sessions and street IDs for the four shipped regions. Fill the rest by hand.

## Adding a host region

1. Draft the preset.
2. Find the street buildings and decide how they are handled.
3. Write the preset under `presets/`.
4. Generate the item list.
5. Add an example config under `examples/`.
6. Add the region to `tests/test_presets.py`.
7. Test in game and update the support table in the README.

## Scanner fixtures

Scanner tests build small mod trees in a temporary folder. When you add a new ModOp pattern:

1. Add a fixture mod to `tests/test_scan_mods.py`.
2. Assert what the scanner should include, report, or warn about.
3. Keep the existing fixture untouched unless the behaviour it checks is intentionally changing.

## Style

- Python 3.10 or newer.
- Standard library only for the shipped tools.
- Type hints on public functions.
- Readable names over clever code.
- Keep command line output short; put detail in the JSON report.
- No absolute paths in shipped code.
- No private mod names, private GUID bands, or personal paths in the repository. The hygiene test enforces the last two points.
- Generated files are not edited by hand. Change the generator and regenerate.

## Release

1. Update `src/version.py`.
2. Update `CHANGELOG.md`.
3. Run the full test suite.
4. Generate all four examples and check the Lua and XML.
5. Update the support table in the README.
6. Commit, tag with `v` plus the version, and push the tag.
7. Create a GitHub release with the notes and the archive.

CI generates the four examples with `--guid-base 1900000000`, a test-only value. The example configs stay empty so users must choose their own range.

The release checklist in `docs/versioning.md` has the same steps with more detail.
