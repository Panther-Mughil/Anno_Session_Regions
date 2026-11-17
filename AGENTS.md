# AGENTS.md

Instructions for an AI coding agent helping a modder use this repository. Read this whole file before changing anything.

## What this repository does

Anno 1800 builds the construction menu from the region, not from the session. A custom session inside the New World inherits the New World tier tabs, and the same is true for the Old World, the Arctic, and Enbesa. This repository generates a small mod that hides the host region's tier tabs inside one custom session and restores the game's normal unlock rules everywhere else.

The tools are Python 3.10 or newer and use only the standard library. The generated mod uses XML triggers and Lua scripts.

## Read first

- `README.md`: what the project is and the quick start.
- `docs/step-by-step.md`: the beginner walkthrough. Point the modder here first.
- `docs/how_it_works.md`: the mechanism, the trigger, and every Lua call.
- `docs/configuration.md`: every config field.
- `docs/regions.md`: the four host regions and their tab IDs.
- `docs/compatibility.md`: the scanner and its limits.
- `docs/troubleshooting.md`: common failures and the approaches that do not work.
- `docs/versioning.md`: version and release rules.

## The one-region rule

One config generates one gate for one host region and one custom session. That is enough for a mod. Do not generate the other three example configs unless the user explicitly asks for another region.

Each example's item list belongs to its own region. Generating the New World config does not touch the Old World, Arctic, or Enbesa. The generator reads only the config you give it.

If the user wants gates for more than one region, each gate needs:

- a different `mod_id`;
- a different `trigger_guid_base` with enough free IDs;
- its own output folder.

Two generated mods with the same trigger GUIDs will define the same assets, and the loader will keep one of them. Do not reuse a base across configs.

## Ask the user before starting

You need these facts. Do not guess any of them.

1. The path to their mod, or at least the folder that contains their session asset and `modinfo.json`.
2. The GUID of their custom session. This is the session asset, not the host session. If they do not know it, search their mod for a `Session` template and show them the candidate GUIDs. Ask them to confirm.
3. The host region: New World, Old World, Arctic, or Enbesa. A session inside Cape Trelawney uses the Old World preset.
4. A free GUID block in their own range. Ask for the first free ID and how many IDs they can spare. Do not invent a range. Do not use `900000100`, `900000500`, or a number from another mod.
5. The path to the game install, so the scanner can read the install `mods` folder. On Linux this is usually required.
6. Whether Streets Unified is installed. It is required. They can use the copy in `companions/streets_unified`; they must install one copy only.
7. Whether they want the generator to write the trigger XML, or skip it so they can add the triggers themselves later.

If the user has no custom session yet, stop. The gate needs a session GUID; it cannot create the session.

## Hard rules

- Use the project AI co-author line on commits: `Co-Authored-By: Aveline (AI) <358026186+Panther-Aveline@users.noreply.github.com>`. Do not add Claude, Anthropic, or other co-author lines.
- Never invent a GUID. Ask for the user's free block.
- Never reuse a trigger base across two generated mods.
- Never put a vanilla building GUID into the user's own region `BuildingList` or unlock trigger. Reference vanilla GUIDs for products, fertilities, text, and icons, but not for the user's own buildings.
- Do not edit generated Lua or XML by hand. Change the config or the templates and regenerate.
- Do not edit the game install outside its `mods` folder and the game's own logs.
- Do not overwrite the user's files without a backup. If a file would be replaced, copy it next to the original first.
- Do not run destructive git commands.
- Do not push, publish, or open a public release without explicit permission.
- Do not claim the mod works in game. The agent cannot launch the game. Ask the user to test and report.
- Read `docs/troubleshooting.md` before proposing a fix. The dead ends listed there have already been tried.

## Workflow

### 1. Inspect the user's mod

- Find `modinfo.json` and the session asset.
- Confirm the session GUID and the host region.
- Check whether the mod already has a construction menu category. If it does, the gate should hide the host tabs, not the user's own category.
- Check for an existing gate. Do not generate a second one with the same trigger IDs.

### 2. Pick one preset

| Host region | Preset |
|---|---|
| New World | `new_world` |
| Old World or Cape Trelawney | `old_world` |
| Arctic | `arctic` |
| Enbesa | `enbesa` |

### 3. Create the config

Copy the matching file from `examples/` into the user's mod project. Fill in:

- `hide_session.guid` and `hide_session.name`: the custom session.
- `mod_id`, `mod_name`, `creator`, `version`: the user's values.
- `trigger_guid_base`: the first free GUID in their block.
- `script_prefix`: a short prefix for the Lua file names.
- `region`: the preset key.

Leave `show_sessions` out unless the user has a reason to change it. The default restores the menu in every vanilla session except the hide session, which is what a normal install needs.

If the user wants to add the triggers themselves, set `"generate_triggers": false` or pass `--skip-triggers` later.

### 4. Run the scanner when the user has other mods

```sh
python src/scan_mods.py --preset new_world \
  --game-dir "/path/to/Anno 1800" \
  --assets "/path/to/assets.xml" \
  --out compat.json
```

- `--assets` is the user's exported `assets.xml`. If they do not have one, omit it and tell them the scanner warns about nested vanilla categories.
- The scanner reads the three mod folders directly. It does not read `mod-loader.log`.
- Read `items`, `new_tabs`, and `warnings` in the report. Items are safe to over-include. New tabs are not locked; tell the user about them.
- If the user has no other mods, skip this step.

### 5. Generate

```sh
python src/generate.py --config path/to/config.json --compat compat.json
```

The output goes to the config's `output`, or `out/<mod_id>` next to the config.

Check the printed summary:

- the region is the one the user chose;
- the module counts are plausible for that region;
- the trigger range is inside the user's block.

### 6. Manual trigger mode

```sh
python src/generate.py --config path/to/config.json --skip-triggers
```

This writes the Lua scripts and `modinfo.json` but not the trigger XML. It writes:

- `menugate.triggers.json`: the machine-readable list of triggers, sessions, scripts, and GUIDs.
- `menugate.triggers.xml.txt`: a copy-ready `<ModOps>` snippet.

The user adds those triggers to their own `assets.xml`, or renames and places the snippet where their mod loads XML. Do not leave the `.xml.txt` file where the loader scans XML; the `.txt` extension keeps it inert, but confirm with the user where they placed it.

The trigger GUIDs are still allocated and recorded in `menugate.config.json`. The user can change them if they keep each one unique and outside the item list; the Lua scripts do not depend on the trigger GUIDs.

### 7. Validate before installing

Run:

```sh
python -m pytest
python tests/check_generated.py
```

If `luac` is installed, check every generated Lua file:

```sh
luac -p path/to/output/data/script/*.lua
```

Check the generated XML:

```sh
python -c "import xml.etree.ElementTree as ET; ET.parse('path/to/output/data/config/export/main/asset/assets.xml')"
```

For manual trigger mode, parse `menugate.triggers.xml.txt` as XML.

Also check:

- every trigger GUID is inside the user's block;
- no trigger GUID is also an item GUID;
- `modinfo.json` lists `Streets_Unified` in `ModDependencies` and `LoadAfterIds`;
- the generated mod has the three Lua files per module.

### 8. Install

Copy the generated mod folder and `companions/streets_unified` into the game's mods folder. Install one copy of Streets Unified. If the user already has the original, tell them to keep one copy only.

Do not merge Streets Unified into the generated gate. Keep them as two mods.

### 9. Test in game

The user must launch the game. Ask them to check:

1. Enter the custom session. The host region's tier tabs should be gone.
2. The Streets tab should still be there.
3. Leave the custom session. The normal menu should return with the progress they earned.
4. Repeat in creative mode if they use it.
5. If they added triggers manually, check that the triggers loaded in the loader log.

If the tabs are still visible, read `docs/troubleshooting.md` before changing anything. The usual causes are a wrong session GUID, missing Streets Unified, or a mod item the scanner missed.

## How many trigger GUIDs are allocated

Each module uses:

```
1 hide + 1 normal restore per show session + 1 creative restore per show session
```

**One custom session with one core module and the default five show sessions uses 11 trigger GUIDs.** Without creative restore it uses 6. With a compatibility module it uses 22, or 12 without creative. The demo hides the New World inside the New World, so it has four show sessions and uses 9.

One region does not reduce the show session count. The gate must restore the menu in every other session the player can enter. If the user has a reason to restore in fewer sessions, they can set `show_sessions` to the sessions they use, but leaving one out means the menu will not restore there.

## Multi-region use

If the user wants gates for several host regions:

1. Create a separate config per region.
2. Give each config a different `mod_id`.
3. Give each config a different `trigger_guid_base`, with enough room for its modules.
4. Generate each into its own output folder.
5. Never install two gates with the same trigger GUIDs.

## Reporting

End with:

- what was generated (region, module count, trigger range);
- where the config and output are;
- which validation commands ran and their results;
- what the user must test in game;
- any warning or unresolved question.

Label claims about the game as CONFIRMED, LIKELY, or UNVERIFIED. Do not present a generated file as proof that the menu works in game.

## Copy-ready prompt for the user

```text
Use the Anno_Session_Regions repository and read AGENTS.md before starting.
My mod is at: <path>
My custom session GUID is: <guid>
My host region is: <New World | Old World | Arctic | Enbesa>
My free GUID block starts at: <guid>
I have Streets Unified installed: <yes | no>
I have other mods installed: <yes | no, or the list>
I want the triggers: <generated | skipped so I can add them myself>
Do not invent GUIDs, do not generate the other regions, and do not push anything.
```
