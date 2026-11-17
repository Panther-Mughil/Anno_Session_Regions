# Step-by-step setup

This guide walks you through one gate for one host region. You do not need to set up all four regions. Pick the region your custom session lives in and follow the steps in order.

The guide uses simple examples. Replace the example values with your own.

## Words used in this guide

- **GUID**: the number that identifies an asset in the game data.
- **Asset**: one thing the game loads, such as a building, a trigger, or a product.
- **Region**: a large area with its own menu, such as the New World or Enbesa.
- **Session**: one map inside a region.
- **Trigger**: a small XML asset that runs a Lua script when a condition is true.
- **Module**: one item list with its own scripts and triggers.

## Before you start

You need:

- Anno 1800 with the in-game mod loader. The shipped presets were made from game version **GU18.4**.
- **Python 3.10 or newer**. The tools use only the standard library.
- A custom session mod of your own. The gate needs the session GUID from that mod.
- **Streets Unified**. It is included in `companions/streets_unified` and is required.
- A **free block of GUIDs** in your mod's own GUID range.
- The path to your Anno 1800 install.

You do not need to create a new region. The gate hides the host region's tier tabs inside your custom session.

## Step 1: Pick your host region

Choose the region your custom session is inside.

| Your custom session is inside | Use this preset |
|---|---|
| New World | `new_world` |
| Old World or Cape Trelawney | `old_world` |
| Arctic | `arctic` |
| Enbesa | `enbesa` |

One config makes one gate. The other presets are alternatives, not extra steps.

## Step 2: Find your session GUID

The gate needs the **GUID of your custom session**, not the GUID of the host region.

1. Open your mod project.
2. Find the session asset. It is the asset with the `Session` template.
3. Read its `<GUID>`.
4. Keep that number. It goes in `hide_session.guid`.

If you do not know the GUID, ask the person who made the session or search your mod files for the session asset. Do not use the New World GUID `180025` unless you are running the demo.

## Step 3: Choose a free GUID block

The gate defines new trigger assets. They need GUIDs that no other mod uses.

1. Open the GUID list or registry for your mod.
2. Find a free block in your own range.
3. Use the **first free ID** as `trigger_guid_base`.
4. Leave enough room. One region with one module uses **11** IDs with the default five show sessions. Two modules use **22**.
5. Do not reuse a block that another generated gate uses.

For example, if your block is `2001202271` to `2001202399`, use `2001202271` as the base. A core plus a compatibility module would use `2001202271` to `2001202292`.

Do not use `900000100` or `900000500`. Those are example placeholders.

## Step 4: Copy one example config

Copy the config for your region into your mod project.

```sh
cp examples/new_world/config.json my_session_gate.json
```

Change the file name to something that makes sense for your mod.

## Step 5: Fill in the basic fields

Open the config in a text editor. Fill these fields first.

| Field | What to put |
|---|---|
| `mod_id` | A unique ID for the generated mod, for example `My_Session_Gate`. |
| `mod_name` | The name players see, for example `My Session Gate`. |
| `creator` | Your name. |
| `version` | Your mod version, for example `1.0.0`. |
| `description` | One short sentence about the gate. |
| `category` | `Gameplay` for a standalone mod, or `Component` if you place it inside an existing mod. |
| `region` | The preset you picked in step 1. |
| `output` | Where the generated folder goes. The default is `out/<mod_id>` next to the config. |

## Step 6: Fill in the session fields

```json
"hide_session": {
  "guid": 900000001,
  "name": "My Custom Session"
}
```

- `guid`: the session GUID from step 2.
- `name`: a readable name. It appears in trigger names, so use something you recognize.

You can leave `show_sessions` out. The generator then restores the menu in every vanilla session except the hide session. That is what a normal install needs.

Only add `show_sessions` if you have a specific reason to limit the restore. Leaving a session out means the menu will not restore there.

## Step 7: Fill in the trigger fields

| Field | What to put |
|---|---|
| `trigger_guid_base` | The first free ID from step 3. **This must not be empty.** |
| `script_prefix` | A short prefix for the Lua files, for example `my_gate`. |
| `marker_dir` | Leave it as `logs`. The game writes the restore marker there. |
| `creative_restore` | Leave it as `true` unless you do not want creative mode handled. |
| `generate_triggers` | Leave it as `true` for normal use. Set it to `false` if you want to add the triggers yourself later. |

If `trigger_guid_base` is empty, the generator stops and tells you to fill it.

## Step 8: Fill in the dependency and metadata fields

```json
"streets_unified": { "required": true },
"dependencies": [],
"known_issues": []
```

- Leave `streets_unified` as required. The gate needs the companion.
- Add extra ModIDs to `dependencies` only if your gate needs another mod.
- Put known problems in `known_issues` if you want them shown in the mod list.

## Step 9: Check the module

The config has one module by default:

```json
"modules": [
  {
    "key": "core",
    "name": "Base game",
    "items_file": "../../presets/items/new_world_core.json"
  }
]
```

- `key`: a short name used in file names. `core` is fine.
- `name`: the name used in trigger names. `Base game` is fine.
- `items_file`: the item list for your region. The path is relative to the config.
- `include`: leave it out to lock the default set: leaves, nested submenus, and tab categories.
- `keep_unlocked`: leave it out to use the region's street buildings.
- `items`: add extra GUIDs by hand if you need them.
- `exclude`: remove GUIDs from the lock list if a mod needs one left alone.
- `enabled`: set it to `false` to skip the module.

The item list already contains the host region's tier tabs. You do not need to edit it by hand.

## Step 10: Scan your installed mods (optional)

If you use other mods, the gate needs to know what they add to the host tier tabs. Run the scanner.

### Windows

```bat
python src\scan_mods.py --preset new_world ^
  --game-dir "C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher\games\Anno 1800" ^
  --assets "C:\path\to\assets.xml" ^
  --out compat.json
```

The scanner finds `%USERPROFILE%\Documents\Anno 1800\mods` and `C:\Users\Public\mod.io\4169\mods` automatically. Pass `--game-dir` if your install is somewhere else.

### Linux

```sh
python3 src/scan_mods.py --preset new_world \
  --game-dir "/path/to/Anno 1800" \
  --assets "/path/to/assets.xml" \
  --out compat.json
```

On Linux the install can be on any mount, so **always pass `--game-dir`**. The scanner reads `<game-dir>/mods`. It finds the Documents and mod.io folders inside common Steam, Wine, and Lutris prefixes automatically.

If your prefix is somewhere unusual, pass `--documents` and `--modio` directly. Use `--print-roots` to see what the scanner checked.

Read `compat.json`:

- `items`: mod buildings the gate should lock. The generator uses these.
- `new_tabs`: mod tabs that stay visible. Add them by hand if you want them hidden.
- `warnings`: things the scanner could not follow. Read them.

If you do not have other mods, skip this step.

## Step 11: Generate the gate

```sh
python3 src/generate.py --config my_session_gate.json
```

If you made a compatibility list:

```sh
python3 src/generate.py --config my_session_gate.json --compat compat.json
```

The generator prints:

- the region it used;
- the number of items and triggers per module;
- the trigger GUID range.

Check that the region and the range are correct.

## Step 12: Understand the output

The generated folder contains:

| File or folder | What it is |
|---|---|
| `modinfo.json` | The mod's name, version, and Streets Unified dependency. |
| `data/config/export/main/asset/assets.xml` | The trigger assets. |
| `data/script/<prefix>_<module>_hide.lua` | Locks the items in your custom session. |
| `data/script/<prefix>_<module>_show.lua` | Restores the game's normal rules outside it. |
| `data/script/<prefix>_<module>_creative.lua` | Handles creative mode. |
| `menugate.config.json` | A record of the config, item counts, and trigger GUIDs. |

Do not edit the generated files by hand. Change the config and generate again.

## Step 13: Add the triggers yourself (optional)

If you want to place the triggers in your own XML, use:

```sh
python3 src/generate.py --config my_session_gate.json --skip-triggers
```

The generator writes the Lua scripts and `modinfo.json`, but not `assets.xml`. It writes:

- `menugate.triggers.json`: the trigger list with GUIDs, sessions, scripts, and kinds.
- `menugate.triggers.xml.txt`: a copy-ready XML snippet.

Add those triggers to your own `assets.xml` using the GUIDs in the manifest. You can change a GUID if you keep it unique and outside the item list. Do not leave the `.xml.txt` file where the loader reads `.xml` files.

## Step 14: Validate before installing

Run the project tests:

```sh
python3 -m pytest
```

Check the generated XML:

```sh
python3 -c "import xml.etree.ElementTree as ET; ET.parse('out/My_Session_Gate/data/config/export/main/asset/assets.xml')"
```

Check the Lua syntax if `luac` is installed:

```sh
luac -p out/My_Session_Gate/data/script/*.lua
```

For manual trigger mode, parse `menugate.triggers.xml.txt` as XML.

## Step 15: Install

1. Copy the generated folder into the game's mods folder.
2. Copy `companions/streets_unified` into the same mods folder.
3. Install **one copy** of Streets Unified. If you already have the original, keep one.
4. Restart the game. XML changes are not read live.

## Step 16: Test in game

Ask the person testing to check:

1. Enter your custom session. The host region's tier tabs should be gone.
2. The Streets tab should still be there.
3. Leave the custom session. The normal menu should return with the progress that player earned.
4. Try creative mode if you use it.
5. Check the loader log if a trigger does not run.

The agent or the tool cannot launch the game. The in-game check is the only proof.

## How many trigger GUIDs will I use?

For **one custom session**, one host region, and the default five show sessions:

| Setting | Trigger GUIDs |
|---|---|
| Core module, creative on | **11** |
| Core module, creative off | **6** |
| Core module plus a compatibility module, creative on | **22** |
| Core module plus a compatibility module, creative off | **12** |
| Demo that hides the New World in the New World | **9** |

The formula per module is `1 hide + N normal restores + N creative restores`, where N is the number of show sessions. One custom session does not need the other three regions.

The gate defines only trigger assets. The item GUIDs in the lists are vanilla IDs. The Streets Unified companion uses fixed IDs 2001229950 to 2001229954 and does not use your block.

## All top-level parameters

| Parameter | Required | What it does |
|---|---|---|
| `schema_version` | No | Must be `1` when present. |
| `mod_id` | Yes | The ModID written to the mod. |
| `mod_name` | Yes | The display name. |
| `creator` | No | Your name. |
| `version` | No | The generated mod version. |
| `description` | No | The description in the mod list. |
| `category` | No | `Gameplay` or `Component`. |
| `region` | Yes | `new_world`, `old_world`, `arctic`, or `enbesa`. |
| `hide_session` | Yes | Your custom session GUID and name. |
| `show_sessions` | No | Sessions where the menu is restored. Default: all vanilla sessions except the hide session. |
| `trigger_guid_base` | Yes | The first trigger GUID. No default. |
| `script_prefix` | Yes | The Lua file prefix. |
| `marker_dir` | No | The restore marker folder. Default `logs`. |
| `creative_restore` | No | Generate the creative scripts. Default `true`. |
| `generate_triggers` | No | Write the trigger XML. Default `true`. |
| `streets_unified` | No | Require the Streets Unified companion. Default `true`. |
| `dependencies` | No | Extra ModIDs to load after. |
| `known_issues` | No | Known issues shown in the mod list. |
| `output` | No | Output folder. Default `out/<mod_id>`. |
| `modules` | Yes | One or more item lists and their scripts. |

## All module parameters

| Parameter | Required | What it does |
|---|---|---|
| `key` | Yes | Short name used in file names. |
| `name` | No | Name used in trigger names. |
| `enabled` | No | Set to `false` to skip the module. |
| `items_file` | No | Item list from `extract_tier_menu.py`. |
| `include` | No | Groups read from the item list. Default: leaves, containers, tabs. |
| `items` | No | Extra GUIDs added by hand. |
| `keep_unlocked` | No | GUIDs removed from the lock list and always unlocked. |
| `exclude` | No | GUIDs removed from the lock list without forcing them unlocked. |
| `creative_restore` | No | Override the top-level creative setting for this module. |

## All generator commands

| Command | What it does |
|---|---|
| `--config PATH` | The config to read. Required. |
| `--preset KEY` | Override the config's region. |
| `--compat PATH` | Add a compatibility module from the scanner. |
| `--guid-base ID` | Override the config's trigger base. |
| `--skip-triggers` | Write the Lua and manifest instead of the trigger XML. |
| `--out PATH` | Override the output folder. |
| `--dry-run` | Print the plan without writing files. |

## What the generator can do

- Make one gate for one host region and one custom session.
- Use a core module and one or more compatibility modules.
- Allocate trigger GUIDs and refuse collisions with item GUIDs.
- Keep street buildings unlocked.
- Generate normal, creative, and hide scripts.
- Add the Streets Unified dependency.
- Write a provenance file with the config hash and trigger range.
- Write a manual trigger manifest when you skip the trigger XML.
- Produce the same output for the same inputs.

## What it cannot do

- It cannot create the session, map, or population.
- It cannot hide the host region's non-tier tabs.
- It cannot create or edit the user's buildings.
- It cannot verify the result in game.
- It does not support multiplayer as a tested case.

## If something goes wrong

- **The generator says `trigger_guid_base` is empty:** fill it, or pass `--guid-base`.
- **The tabs are still visible:** check the session GUID, Streets Unified, and the scanner report.
- **The roads are missing:** check Streets Unified and the `keep_unlocked` list.
- **The menu is locked everywhere:** read the marker and show trigger sections in `docs/troubleshooting.md`.

The full guide is in `docs/configuration.md` and `docs/troubleshooting.md`.
