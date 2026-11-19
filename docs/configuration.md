# Config reference

New to the project? Read `docs/step-by-step.md` first. It explains the fields in order.

The generator reads one JSON file. The examples under `examples/` are complete configs you can copy.

## Top level

| Field | Required | Meaning |
|---|---|---|
| `schema_version` | No | Must be `1` when present. The default is `1`. |
| `mod_id` | Yes | The `ModID` written to `modinfo.json`. Use a name that belongs to your mod. |
| `mod_name` | Yes | The display name. |
| `creator` | No | The `CreatorName` field. |
| `version` | No | The generated mod version. Default `0.1.0`. |
| `description` | No | The description shown in the mod list. |
| `category` | No | The mod category. Default `Gameplay`. Use `Component` if you install the generated folder as a component of an existing mod. |
| `region` | Yes | The preset key: `new_world`, `old_world`, `arctic`, or `enbesa`. |
| `hide_session` | Yes | An object with `guid` and `name`. The custom session where the host tabs are hidden. |
| `show_sessions` | No | A list of sessions where the menu is restored. Default: every vanilla session except the hide session. |
| `trigger_guid_base` | Yes | The first of the trigger GUIDs. No default; the examples use `null`. The generator stops until it is set, or until `--guid-base` is passed. |
| `script_prefix` | Yes | The prefix for the generated Lua file names. |
| `marker_dir` | No | The folder for the restore markers and the runtime log. Default `logs`. |
| `marker_max_age_seconds` | No | How long a restore marker stays valid. Default `21600` (6 hours). Must be positive. |
| `session_enter_delay_ms` | No | The generic restore's arrival cue, in milliseconds. Default `500`. |
| `creative_restore` | No | Generate the creative scripts and creative triggers. Default `true`. |
| `generate_triggers` | No | Write the trigger XML. Default `true`. Set to `false` to write a manual trigger manifest instead. |
| `log_file` | No | The runtime log path, relative to the game's working folder. Default `<marker_dir>/<script_prefix>.log`. |
| `log_backup` | No | The rotated log path. Default replaces `.log` with `.prev.log`. |
| `log_cursor` | No | The dedupe cursor path. Default replaces `.log` with `.cursor`. |
| `log_rotate_bytes` | No | Rotate the log at this size. Default `262144` (256 KB). |
| `log_dedupe_seconds` | No | Suppress an identical log line inside this window. Default `60`. `0` disables dedupe. |
| `known_sessions` | No | A list of `{ "guid", "name", "region"?, "region_name"? }` used for log labels only. It never creates a trigger. Default: `presets/sessions.json` plus `hide_session`. |
| `streets_unified` | No | `{ "required": true }` adds the Streets Unified dependency. Default `true`. |
| `dependencies` | No | Extra ModIDs added to `ModDependencies` and `LoadAfterIds`. |
| `load_after` | No | Extra ModIDs added to `LoadAfterIds` only. |
| `known_issues` | No | A list written to `KnownIssues` in `modinfo.json`. |
| `output` | No | The output folder, relative to the config. Default `out/<mod_id>`. |
| `modules` | Yes | One or more modules. See below. |

### hide_session

```json
"hide_session": { "guid": 900000001, "name": "My Custom Session" }
```

`guid` must be the session asset your mod defines. If it is wrong, the hide trigger never runs.

### show_sessions

```json
"show_sessions": [
  { "guid": 180025, "name": "New World" },
  { "guid": 180023, "name": "Old World" }
]
```

Leave it out to use every session in `presets/sessions.json` except the hide session. The hide session must not appear in this list; the generator stops with an error if it does.

### trigger_guid_base

Each module uses, with `N` show sessions:

- 1 GUID for the hide trigger;
- `N` GUIDs for the named restore triggers;
- `N` GUIDs for the named creative restore triggers, when creative restore is on;
- 1 GUID for the generic restore trigger, plus 1 for its creative twin;
- 1 GUID for the settle flag, 1 for the settle trigger and 1 for its creative twin.

That is `2N + 6` with creative restore, or `N + 4` without it. With the default five show sessions, one module uses 16 GUIDs (9 without creative). Two modules use 32 (18 without creative). The generator checks that no trigger GUID is also an item GUID.

Use a free block in your own GUID range. The examples set this to `null` on purpose because the toolkit does not own a range. The generator stops with an error until you fill it, or pass `--guid-base` on the command line. The generator cannot check a band against vanilla or against other installed mods.

One config generates one gate for one host region. The other example configs are alternatives, not extra steps. If you generate more than one region, give each config its own `mod_id` and `trigger_guid_base`; two gates with the same trigger GUIDs will collide.

## Trigger count

Each module uses one hide trigger, one named restore and one named creative restore per show session, one generic restore and creative generic, one settle flag, and one settle trigger and creative settle. With the default five show sessions that is 16 per module. Two modules use 32.

For **one custom session with one core module and the default settings, the answer is 16 trigger GUIDs.** Without creative restore it is 9. With a compatibility module it is 32 (or 18 without creative). If the hide session is one of the five vanilla sessions, there are four show sessions, so the count is 14 (or 8 without creative).

The item GUIDs in the lock lists are vanilla IDs. The gate defines only new trigger assets. The Streets Unified companion uses fixed IDs 2001229950 to 2001229954 and does not consume your block.

One region does not reduce the show session count. The gate must restore the menu in every other session the player can enter. If you have a reason to restore in fewer sessions, set `show_sessions` to the ones you use.

## Manual triggers

Set `"generate_triggers": false` or pass `--skip-triggers`. The generator still writes the Lua scripts, `modinfo.json`, and the provenance file, but it does not write `data/config/export/main/asset/assets.xml`. It writes two files at the mod root instead:

- `menugate.triggers.json`: the trigger list with GUIDs, sessions, scripts, and kinds.
- `menugate.triggers.xml.txt`: the same triggers as a copy-ready `<ModOps>` snippet.

The trigger GUIDs are still allocated and recorded in `menugate.config.json`. Add the triggers to your own `assets.xml` using those GUIDs, or rename and place the snippet where your mod loads XML. If you change a GUID in the manifest, keep it unique and keep it out of the item list; the Lua scripts do not depend on the trigger GUIDs. Do not leave the `.xml.txt` file where the loader scans `.xml` files; the `.txt` extension keeps it inert.

## Modules

| Field | Required | Meaning |
|---|---|---|
| `key` | Yes | A short name used in the Lua file names and the provenance file. |
| `name` | No | The display name used in trigger names. Default: the key. |
| `enabled` | No | Set to `false` to leave a module out. Default `true`. |
| `items_file` | No | A JSON item list from `extract_tier_menu.py`. Paths are relative to the config file. |
| `include` | No | Which groups to read from the item file. Default `["leaves", "containers", "tabs"]`. |
| `items` | No | Extra GUIDs added to the module. Useful for manual compatibility entries. |
| `keep_unlocked` | No | GUIDs removed from the lock list and force-unlocked in every script. Default: the preset's street buildings. |
| `exclude` | No | GUIDs removed from the lock list without forcing them unlocked. |
| `creative_restore` | No | Override the top-level creative setting for this module. |
| `guid_base` | No | Pin this module's first sequential trigger GUID. Default: continue from the previous module's cursor. |
| `guids` | No | Pin individual triggers: `hide`, `generic_restore`, `generic_restore_creative`, `settle_flag`, `settle_restore`, `settle_restore_creative`. An unknown slot is an error. |

The generator allocates every sequential GUID and every pinned GUID through one collision check before it writes anything. A collision, a duplicate module key, or a trigger GUID that is also an item GUID stops the run with nothing written.

Example:

```json
"modules": [
  {
    "key": "core",
    "name": "Base game",
    "items_file": "../../presets/items/new_world_core.json"
  },
  {
    "key": "compat",
    "name": "Installed mods",
    "items_file": "compat.json",
    "items": [123456]
  }
]
```

## Compatibility file

`scan_mods.py` writes an object with an `items` list. Pass it with `--compat`. The generator adds a module named `compat` if the config does not already have one.

```json
{
  "items": [
    { "guid": 123456, "source_mod": "Example_Mod" }
  ]
}
```

`items` may also be a list of plain GUIDs.

## Generated files

The generator writes:

```
modinfo.json
data/config/export/main/asset/assets.xml
data/script/<prefix>_<module>_hide.lua
data/script/<prefix>_<module>_show.lua
data/script/<prefix>_<module>_creative.lua
menugate.config.json
```

`menugate.config.json` is a record of the inputs, the allocated GUIDs and the trigger list. The game does not read it.

The scripts also write runtime files beside the game's other logs, relative to the game's working folder: `logs/<prefix>.log`, `logs/<prefix>.prev.log`, `logs/<prefix>.cursor`, and the two restore markers `logs/<prefix>_<module>.restore` and `logs/<prefix>_<module>.restore_creative`. Create `logs/menugate_debug.off` to silence the log.

The generator stages every output as `<file>.tmp` and renames them into place only after all of them are generated, so an interrupted run cannot pair new scripts with old XML.

Do not edit the generated files by hand. Change the config or `src/generate.py` and regenerate.

## A complete config

```json
{
  "schema_version": 1,
  "mod_id": "My_Session_Gate",
  "mod_name": "My Session Gate",
  "creator": "Your name",
  "version": "0.1.0",
  "description": "Hides the host tier tabs inside my custom session.",
  "category": "Gameplay",
  "region": "new_world",
  "hide_session": { "guid": 900000001, "name": "My Custom Session" },
  "trigger_guid_base": 900000100,
  "script_prefix": "my_gate",
  "marker_dir": "logs",
  "streets_unified": { "required": true },
  "modules": [
    {
      "key": "core",
      "name": "Base game",
      "items_file": "items/new_world_core.json"
    }
  ]
}
```
