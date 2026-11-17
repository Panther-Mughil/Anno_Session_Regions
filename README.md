# Anno Session Regions

A session-scoped construction menu gate for Anno 1800, with a mod scanner and a guide.

[![CI](https://github.com/Panther-Mughil/Anno_Session_Regions/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Panther-Mughil/Anno_Session_Regions/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0--alpha.1-orange.svg)](CHANGELOG.md)

## What this is

Anno 1800 builds the construction menu from the region, not from the session. A mod that adds a new session inside an existing region inherits that region's whole build menu. This project hides the host region's tier tabs while the player is in the custom session, then puts the game's normal unlock rules back when the player leaves.

It works for custom sessions based on the New World, the Old World, the Arctic, or Enbesa.

The project ships:

- a generator that writes the gate mod from a small JSON config;
- item lists for the four host regions, generated from the game's own data;
- a scanner that finds what installed mods add to the host menu;
- the Streets Unified companion mod, which the gate requires;
- this guide and the deeper documents under `docs/`.

## Status

**Alpha, version 0.1.0-alpha.1.**

The gate mechanism has been tested in game for the **New World** in normal and creative saves. The Old World, Arctic, and Enbesa presets are generated from the same vanilla data and pass the local tests, but they have **not been tested in game yet**. The mod scanner is experimental and may miss unusual mod edits.

| Host region | Preset | Locked items after streets | In-game test |
|---|---|---|---|
| New World | `new_world` | 110 | Yes |
| Old World | `old_world` | 148 | Not yet |
| Arctic | `arctic` | 35 | Not yet |
| Enbesa | `enbesa` | 63 | Not yet |

If you test one of the three untested regions, please open an issue with the result. That is how the support table will grow.

## What the gate does and does not do

It does:

- hide the host region's tier tabs inside one session;
- restore the game's own progression rules in every other session;
- keep streets available in every session through Streets Unified;
- generate a separate module for mod-added items, so each group can be updated alone.

It does not:

- create the custom session, map, or population;
- hide the host region's non-tier tabs, such as harbor or ornaments;
- change population needs, products, or buildings;
- restore menus by copying a snapshot of what was unlocked. That reports the game's defaults and over-unlocks saves.

## Requirements

- Anno 1800 with the in-game mod loader (GU17 or newer). The shipped presets were generated from game version GU18.4.
- Python 3.10 or newer. The tools use only the standard library, so there is nothing to install to run them.
- The Streets Unified companion, included in `companions/streets_unified`. The gate declares it as a dependency.
- A custom session of your own, already defined by your mod. The gate needs its session GUID.

Python packages are only needed for development. Run `pip install -r requirements-dev.txt` to get pytest.

## Quick start

1. Copy a region config from `examples/` into your mod project. This walkthrough uses `examples/new_world/config.json`.
2. Open the config and set these fields:
   - `hide_session.guid`: the GUID of your custom session.
   - `hide_session.name`: a readable name, used in trigger names.
   - `mod_id`, `mod_name`, `creator`, and `version`: your mod's values.
   - `trigger_guid_base`: the first of eleven GUIDs the gate will define. Use a free block in your own range. The example configs leave it empty on purpose; the generator stops until you fill it or pass `--guid-base`.
   - `script_prefix`: a short prefix for the generated Lua files.
3. Run the generator:

   ```sh
   python src/generate.py --config path/to/your/config.json
   ```

   The output goes to the config's folder under `out/<mod_id>` unless you pass `--out`.
4. Copy the generated folder and `companions/streets_unified` into the game's mods folder.
5. Start the game and enter your custom session. The host region's tier tabs should be gone. Leave the session and the normal menu should return with the progress you actually earned.
6. If you use other mods, run the scanner and generate again with the compatibility list. See [Compatibility](#compatibility).

The four region configs are templates. They hide nothing until you replace the placeholder session GUID. The demo is the only runnable example.

To see the gate work without making a custom session, use `examples/demo_new_world/config.json`. It hides the New World tier tabs while you are in the New World. That is a test only; remove it after checking.

## How it works

This section is the short version. `docs/how_it_works.md` explains every call and every trigger.

### Region and session

A region is a ruleset and a set of menus: the Old World, the New World, the Arctic, or Enbesa. A session is one map inside a region. The normal New World and your custom New World session are two sessions in the same region.

The construction menu belongs to the region. That is why a custom session inside the New World opens with the Jornaleros, Obreros, and Artistas tabs.

### The rule the gate depends on

A tab is shown when at least one building inside it is available. There is no switch that hides a tab directly. This was tested: locking the tab's category did nothing, and locking every building inside the tab hid it.

So the gate hides a tab by locking every building in it. The reverse matters too: one building left available keeps the whole tab visible.

### Base game only

Using the New World as the example:

1. `src/extract_tier_menu.py` reads the game's `assets.xml` and walks the three tier tabs. It writes the list of items: 101 building leaves (two of them streets), 8 nested submenus, and the 3 tab categories, for 112 IDs.
2. Two of those IDs are the New World streets, `101308` and `101309`. The generator moves them to the keep-unlocked list, which leaves 110 items to lock.
3. `src/generate.py` writes a small mod: `modinfo.json`, one XML trigger per session, and three Lua files per module.
4. When you enter the custom session, the hide trigger runs `hide.lua`. It locks every item on the list. Every building in the three tabs is unavailable, so the tabs disappear.
5. When you leave, a show trigger runs `show.lua`. It does not hand out unlocks. For each item it asks the game which unlock trigger normally gives that item, then asks the game to register that trigger for the player again. The game then recalculates what the player earned. This is why a new player does not get the whole menu back.
6. A marker file in the game's `logs` folder makes the restore one-shot per visit. The hide script deletes the marker, so the next visit restores again.
7. In creative mode the game does not run progression triggers, so `creative.lua` unlocks every item directly.
8. The trigger uses `ConditionActiveSession` and re-checks every 2 seconds. A save that loads straight into the session, or a save made before the mod existed, still gets the right state. This was a real bug in an early version: a one-shot "player entered the session" event never fired on those saves.

### Streets Unified and why it is mandatory

Streets are buildings inside the tier tabs, and the game keeps them available all the time. That breaks the lock-everything rule:

- Lock the streets with the rest of the tab and the player cannot build roads.
- Leave them available and one available building keeps the tab visible.

The same building cannot be locked in one session and unlocked in another, because unlock state belongs to the player, not the session. The scripts change it when the session changes. A building that must always be available cannot take part in that change.

Streets Unified moves the streets of all four regions into their own Streets tab, removes them from the tier tabs, and unlocks them in every session. The gate never locks the Streets tab, so roads stay available and the tier tabs can be emptied.

The companion is in `companions/streets_unified`. See `companions/README.md` for the per-region IDs.

### With mods

A mod can add buildings to a vanilla tier tab. The core list knows the base game, not that mod, so the mod's building stays available and the tab reappears with one item.

1. `src/scan_mods.py` scans the game's mod folders, reads each mod's XML edits, and records what the mod adds to the host region's tier tabs. It writes `compat.json`.
2. `src/generate.py --compat compat.json` adds a separate compatibility module. The core module does not change. Each module has its own Lua files and triggers.
3. Entering the custom session now locks the base game items and the mod items. Leaving restores both modules.

A mod that adds its own new tab is a different case. That tab is not a base game tier tab, so the scanner reports it under `new_tabs` and leaves it visible. Add it by hand if your custom session should hide it.

The scanner understands the common ModOp forms: `add`, `addNextSibling`, `addPrevSibling`, `insert`, `merge`, and `remove`. It is experimental because an unusual mod edit can slip past it. The failure direction matters: missing an item leaves it visible in the custom session, while locking an extra item does nothing. The report lists every item and the mod it came from.

### The parts of this project

| Part | What it does |
|---|---|
| `presets/<region>.json` | The menu node, tier tabs, street IDs, and host sessions for one region. |
| `presets/items/<region>_core.json` | The generated item list: tabs, nested submenus, and leaves. |
| `src/extract_tier_menu.py` | Reads the game's `assets.xml` and writes an item list. |
| `src/discover_regions.py` | Reads the region menus and drafts presets after a game update. |
| `src/scan_mods.py` | Scans installed mods and writes a compatibility list. Experimental. |
| `src/generate.py` | Writes the gate mod from a config, a preset, and optional compatibility list. |
| `templates/*.lua` and `templates/*.xml` | The gate scripts and trigger shapes. Do not edit generated copies. |
| `companions/streets_unified` | The required street companion mod. |
| `examples/` | Configs for each host region, plus a New World demo. |
| `tests/` | Fixture mods, generator checks, preset checks, and repository checks. |

## Compatibility

The scanner reads the three folders the loader scans:

1. `<game install>/mods`
2. `Documents/Anno 1800/mods` inside the Windows or Wine user folder
3. `C:/users/Public/mod.io/4169/mods`

On Linux, pass `--game-dir` because the install can be on any mount. The Documents and mod.io folders inside common Wine and Steam prefixes are found automatically.

It does not read `mod-loader.log`. That log only describes the last launch and misses anything downloaded since.

It respects `activations.json` and the `-` folder prefix, and when two folders hold the same ModID it keeps the higher version. The loader's exact order between folders is not documented, so the scanner warns when it has to choose.

Example:

```sh
python src/scan_mods.py --preset new_world \
  --game-dir "/path/to/Anno 1800" \
  --assets "/path/to/assets.xml" \
  --out compat.json

python src/generate.py --config examples/new_world/config.json --compat compat.json
```

`--assets` lets the scanner expand nested vanilla categories. Without it, the scanner warns that part of the menu is unreadable.

## Supported regions

The presets cover the four vanilla host regions. See `docs/regions.md` for the tab IDs, item counts, and the test status of each one. If a game update changes the menu, run `src/discover_regions.py` to draft new presets and compare them with the shipped ones.

## Documentation

- `docs/how_it_works.md`: the full explanation, including what each Lua call does.
- `docs/streets_unified.md`: the street problem in detail.
- `docs/regions.md`: the four host regions and their tab IDs.
- `docs/configuration.md`: every config field and a complete example.
- `docs/compatibility.md`: the scanner, its limits, and manual overrides.
- `docs/troubleshooting.md`: symptoms, causes, and the approaches that do not work.
- `docs/versioning.md`: alpha status, tags, and how updates are shipped.
- `docs/faq.md`: short answers to common questions.
- `docs/development.md`: repository layout, tests, and the release checklist.
- `CONTRIBUTING.md`: how to report a bug, suggest a change, or send a pull request.
- `CHANGELOG.md`: what changed in each version.

## Versioning

The project follows semantic versioning with pre-release tags. The current version is `0.1.0-alpha.1`. Releases are tagged `v0.1.0-alpha.1` and later. The generated mod carries the toolkit version in its file headers and in `menugate.config.json`, so a generated folder can always be traced back to the tool that made it.

The version stays in the alpha range until every supported host region has had an in-game pass. See `docs/versioning.md`.

## Reporting bugs and asking questions

Open an issue on GitHub. The issue templates ask for the game version, host region, config, mod list, and the loader log. You do not need to be a programmer to report a problem; a clear description and the files the template asks for are enough.

For a security concern, read `SECURITY.md` before posting details in public.

## Contributing

Contributions are welcome, including translations of the guide, new region presets, and scanner fixes. Read `CONTRIBUTING.md` first. The project uses the Contributor Covenant code of conduct.

## License and credits

MIT. You may use, change, and share this project for any purpose. The only condition is that you keep the copyright notice and the license text with copies of the project. See `LICENSE`.

Streets Unified is by Panther and is included under the same license.

Anno 1800 is a trademark of Ubisoft. This project is not affiliated with or endorsed by Ubisoft.
