# Anno Session Regions

A session-scoped construction menu gate for Anno 1800, with a mod scanner and a guide.

[![CI](https://github.com/Panther-Mughil/Anno_Session_Regions/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Panther-Mughil/Anno_Session_Regions/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0--alpha.5-orange.svg)](CHANGELOG.md)

> **New to the project? Read the [step-by-step setup guide](docs/step-by-step.md) first.** It walks through one region, one config, and one generated mod in plain English.

Anno 1800 builds the construction menu from the **region**, not from the **session**. A custom session inside the New World inherits the New World tier tabs, and the same happens inside the Old World, the Arctic, and Enbesa. This project generates a small mod that hides the host region's tier tabs inside your custom session and restores the game's normal unlock rules everywhere else.

**Contents:** [Status](#status) · [Roadmap](#roadmap) · [Quick start](#quick-start) · [How it works](#how-it-works) · [Compatibility scanner](#compatibility-scanner) · [Supported regions](#supported-regions) · [Documentation](#documentation) · [Credits](#credits)

## At a glance

| Item | Details |
|---|---|
| **What it is** | A reusable session menu gate, a region preset set, a mod scanner, and a guide. |
| **Host regions** | New World, Old World, Arctic, Enbesa. |
| **Status** | **Alpha.** Only the New World has an in-game pass. |
| **Python** | 3.10 or newer. The tools use only the standard library. |
| **Companion** | **Streets Unified**, included in `companions/streets_unified`. Required. |
| **License** | **MIT**, with a request to credit Panther when you publish a mod. |

## Status

**Alpha, version `0.1.0-alpha.5`.**

The gate mechanism has been tested in game for the **New World** in normal and creative saves. The Old World, Arctic, and Enbesa presets are generated from the same vanilla data and pass the local tests, but they **have not been tested in game yet**. The compatibility scanner is **experimental**.

| Host region | Preset | Locked items after streets | In-game test |
|---|---|---|---|
| New World | `new_world` | 110 | **Yes** |
| Old World | `old_world` | 148 | **Not yet** |
| Arctic | `arctic` | 35 | **Not yet** |
| Enbesa | `enbesa` | 63 | **Not yet** |

*A report from any of the three untested regions moves it from beta to tested. Open an issue with the result.*

## Roadmap

| Status | Item |
|---|---|
| **Planned** | Suppress notification toasts when unlocking items. |
| **Planned** | Find better ways to merge streets back into the building tabs. |
| **Planned** | Add compatibility discovery with more mods. |
| **In progress** | Compatibility with other modded sessions. |

The details and the done criteria are in [docs/roadmap.md](docs/roadmap.md).

## What it does

- Hides the host region's **tier tabs** inside one custom session.
- Restores the game's **own progression rules** in every other session.
- Keeps **streets available** through the Streets Unified companion.
- Generates a separate **compatibility module** for mod-added items.
- Can **skip the trigger XML** and write a manual trigger manifest instead.
- Records the **trigger range and config hash** in the generated output.

## What it does not do

- It does not create the session, map, or population.
- It does not hide the host region's non-tier tabs, such as harbor or ornaments.
- It does not change products, needs, or buildings.
- It does not restore menus from a snapshot. That over-unlocks saves.
- It does not read `mod-loader.log`.
- It cannot test the result in game for you.

## Requirements

- Anno 1800 with the in-game mod loader. The shipped presets were made from **GU18.4**.
- **Python 3.10 or newer**.
- A custom session mod of your own, with a session GUID.
- The **Streets Unified** companion.
- A free block of GUIDs in your mod's own range.
- Your game install path.

## Quick start

1. **Pick one region config** from `examples/`. *You do not need the other three.* This walkthrough uses `examples/new_world/config.json`.
2. **Fill `hide_session.guid` and `trigger_guid_base`.** The examples leave the trigger base empty on purpose. The generator stops until you fill it. Use a free block in your own range.
3. **Generate the gate.**

   ```sh
   python3 src/generate.py --config path/to/your/config.json
   ```

4. **If you use other mods, scan them and generate again.**

   ```sh
   python3 src/scan_mods.py --preset new_world --game-dir "/path/to/Anno 1800" --out compat.json
   python3 src/generate.py --config path/to/your/config.json --compat compat.json
   ```

5. **Copy the generated folder and `companions/streets_unified`** into the game's mods folder. Install **one copy** of Streets Unified.
6. **Test in game.** Enter your custom session. The host tier tabs should be gone. Leave the session. The normal menu should return with the progress the player earned.

The full walkthrough, every parameter, and every command are in the **[step-by-step setup guide](docs/step-by-step.md)**.

## How it works

### The problem

The construction menu belongs to the region. A custom session inside the New World opens with the Jornaleros, Obreros, and Artistas tabs. The gate removes those tabs **only while the player is in your session**.

### The rule the gate uses

A tab is shown when **at least one building inside it is available**. There is no switch that hides a tab directly. This was tested:

- Locking the tab's category did nothing.
- Locking every building inside the tab hid it.

So the gate hides a tab by locking every building in it. The reverse also matters: **one available building keeps the whole tab visible**.

### The moving parts

| Part | What it does |
|---|---|
| `presets/<region>.json` | The region menu node, tier tabs, street IDs, and host sessions. |
| `presets/items/<region>_core.json` | The generated item list: tabs, nested submenus, and leaves. |
| `src/extract_tier_menu.py` | Reads the game's `assets.xml` and writes an item list. |
| `src/discover_regions.py` | Drafts presets after a game update. |
| `src/scan_mods.py` | Finds what installed mods add to the host tier tabs. **Experimental.** |
| `src/generate.py` | Writes the gate mod from a config, a preset, and an optional compatibility list. |
| `templates/*.lua` and `templates/*.xml` | The generated scripts and trigger shapes. |
| `companions/streets_unified` | The required street companion. |
| `examples/` | A config per region, plus a New World demo. |
| `tests/` | Fixture mods, generator checks, preset checks, and repository checks. |

### Base game example

1. `src/extract_tier_menu.py` lists the host region's tier tabs. For the New World, that is 101 leaves (99 buildings and 2 streets), 8 nested submenus, and 3 tab categories, for **112 items**.
2. Two of those are the New World streets, `101308` and `101309`. The generator moves them to the **keep-unlocked** list, leaving **110 items to lock**.
3. Entering the custom session runs `hide.lua`, which locks all 110 items. The three tabs have nothing available, so they disappear.
4. Leaving the session runs `show.lua`. It does **not** hand out unlocks. It asks the game which trigger normally grants each item, then registers those triggers again. The game recalculates what the player earned.
5. A marker file makes the restore one-shot per visit. The hide script deletes it, so the next visit restores again.
6. Creative mode has no progression. A separate script unlocks the items directly.
7. The trigger re-checks every **2 seconds**, so a save that loads directly into the session, or a save made before the mod existed, still gets the right state.

The full trigger and Lua explanation is in [docs/how_it_works.md](docs/how_it_works.md).

### Streets Unified and why it is required

Streets are buildings inside the tier tabs, and the game keeps them available all the time. The gate cannot both lock and keep a building available:

- **Lock the streets** and the player cannot build roads in the custom session.
- **Leave them available** and one available building keeps the tab visible.

Unlock state belongs to the player, not the session. A building that must stay available all the time cannot take part in the session flip.

Streets Unified moves each region's streets into their own **Streets tab**, removes them from the tier tabs, and unlocks them in every session. The gate never locks that tab, so roads stay available and the tier tabs can be emptied. See [docs/streets_unified.md](docs/streets_unified.md).

### With mods

A mod can add buildings to a vanilla tier tab. The core list does not know them, so they stay available and the tab reappears.

1. `src/scan_mods.py` reads the installed mods and writes `compat.json`.
2. `src/generate.py --compat compat.json` adds a **separate compatibility module**.
3. Entering the session locks the base items and the mod items. Leaving restores both modules.

A mod that adds its own **new tab** is reported under `new_tabs` and left visible. Add it by hand if your session should hide it.

## Compatibility scanner

The scanner reads the mod folders directly. It does **not** read `mod-loader.log`, because that log only describes the last launch and misses anything downloaded since.

### Windows

| Folder | Path | How the scanner finds it |
|---|---|---|
| Install mods | `<game install>\mods` | Pass `--game-dir` if auto-detection misses it. |
| Documents mods | `%USERPROFILE%\Documents\Anno 1800\mods` | Found automatically. |
| mod.io mods | `C:\Users\Public\mod.io\4169\mods` | Found automatically. |

```bat
python src\scan_mods.py --preset new_world --game-dir "C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher\games\Anno 1800" --out compat.json
```

### Linux

The game install can be on any mount, so **always pass `--game-dir`**. The scanner reads `<game-dir>/mods`.

| Folder | Common path | How the scanner finds it |
|---|---|---|
| Install mods | `/path/to/Anno 1800/mods` | Pass `--game-dir`. |
| Steam Proton Documents | `~/.steam/steam/steamapps/compatdata/916440/pfx/drive_c/users/steamuser/Documents/Anno 1800/mods` | Found automatically, including `~/.local/share/Steam` and the Flatpak path. |
| Wine Documents | `~/.wine/drive_c/users/<user>/Documents/Anno 1800/mods` | Found automatically. |
| Lutris Documents | `~/Games/<game>/drive_c/users/<user>/Documents/Anno 1800/mods` | Found automatically. |
| mod.io | `.../drive_c/users/Public/mod.io/4169/mods` | Found automatically inside the prefixes above. |

```sh
python3 src/scan_mods.py --preset new_world --game-dir "/path/to/Anno 1800" --out compat.json
```

If your prefix is somewhere unusual, pass `--documents` and `--modio` directly. Use `--print-roots` to see every folder the scanner checked, `--mods-root` for an extra folder, and `--no-autodetect` to scan only the folders you pass.

### What the scanner respects

- **`activations.json`**: mods listed in `disabledIds` are skipped.
- **The `-` folder prefix**: a disabled mod.
- **Duplicate ModIDs**: the **higher version** wins. The loader's exact order between folders is not documented, so the scanner warns when it has to choose.
- **Symlinks and components**: followed, like the loader does.
- **`.lnk` folder links**: followed when the target is a folder.
- **`.zip` mods**: **not scanned**. The scanner warns and asks you to extract the folder.

### What the scanner does not do

- It does not read `mod-loader.log`.
- It does not scan zip mods.
- It cannot know a mod's runtime behaviour. It reads the files as written.
- It cannot guarantee it understood every possible mod edit. **Over-inclusion is safe**: locking an item that is not in the menu does nothing. Missing an item leaves it visible in your session.

The full scanner reference is in [docs/compatibility.md](docs/compatibility.md).

## Supported regions

| Region | Preset | Tier tabs | Items to lock | In-game test |
|---|---|---|---|---|
| New World | `new_world` | 3 | 110 | **Yes** |
| Old World | `old_world` | 7 | 148 | **Not yet** |
| Arctic | `arctic` | 2 | 35 | **Not yet** |
| Enbesa | `enbesa` | 2 | 63 | **Not yet** |

A custom session inside **Cape Trelawney** uses the `old_world` preset. The tab IDs and the test status of each region are in [docs/regions.md](docs/regions.md).

## Documentation

| Document | What it covers |
|---|---|
| **[Step-by-step setup](docs/step-by-step.md)** | **Start here.** One region, one config, one generated mod, every parameter. |
| [Configuration reference](docs/configuration.md) | Every field and every command. |
| [How it works](docs/how_it_works.md) | The trigger, the Lua calls, and the marker. |
| [Streets Unified](docs/streets_unified.md) | Why the companion is required. |
| [Regions](docs/regions.md) | The four host regions and their tab IDs. |
| [Compatibility](docs/compatibility.md) | The scanner, its limits, and manual entries. |
| [Troubleshooting](docs/troubleshooting.md) | Symptoms, causes, and the approaches that do not work. |
| [Roadmap](docs/roadmap.md) | Planned work and done criteria. |
| [Versioning](docs/versioning.md) | Alpha status, tags, and releases. |
| [FAQ](docs/faq.md) | Short answers. |
| [Development](docs/development.md) | Repository layout, tests, and the release checklist. |
| [AGENTS.md](AGENTS.md) | A workflow for an AI coding agent helping a modder. |
| [Examples](examples/README.md) | The region configs and the demo. |
| [Companion](companions/README.md) | Streets Unified. |
| [Contributing](CONTRIBUTING.md) | Bug reports, pull requests, and code style. |
| [Changelog](CHANGELOG.md) | What changed in each version. |
| [Credits](CREDITS.md) | Authorship and attribution. |

## Versioning

The project follows **semantic versioning** with pre-release tags. The current version is **`0.1.0-alpha.5`**. Releases are tagged `v0.1.0-alpha.5` and later.

The generated mod carries the toolkit version in its file headers and in `menugate.config.json`, so a generated folder can always be traced back to the tool that made it. The version stays in the alpha range until every supported host region has had an in-game pass. See [docs/versioning.md](docs/versioning.md).

## Credits

**If you publish a mod that uses this project, credit Panther and link to the [Anno_Session_Regions](https://github.com/Panther-Mughil/Anno_Session_Regions) repository.**

*A line in your mod description is enough.*

Streets Unified is by Panther and is included under the same license.

**[Aveline (AI)](https://github.com/Panther-Aveline)** is the AI assistant that helped build the project. More in [CREDITS.md](CREDITS.md).

Anno 1800 is a trademark of Ubisoft. This project is not affiliated with or endorsed by Ubisoft.

## Reporting bugs and asking questions

Open an issue on GitHub. The templates ask for the game version, host region, config, mod list, and loader log. You do not need to be a programmer to report a problem. A clear description and the files the template asks for are enough.

For a security concern, read [SECURITY.md](SECURITY.md) before posting details in public.

## Contributing

Contributions are welcome, including region test reports, documentation fixes, new presets, and scanner improvements. Read [CONTRIBUTING.md](CONTRIBUTING.md) first. The project uses the [Contributor Covenant](CODE_OF_CONDUCT.md).

## License

**MIT.** You may use, change, and share the project. Keep the copyright notice and license text with copies. **If you publish a mod that uses it, credit Panther and link to this repository.** See [LICENSE](LICENSE) for the MIT text and [NOTICE](NOTICE) for the credit request.
