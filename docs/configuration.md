# Config reference

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
| `marker_dir` | No | The folder for the restore marker. Default `logs`. |
| `creative_restore` | No | Generate the creative scripts. Default `true`. |
| `streets_unified` | No | `{ "required": true }` adds the Streets Unified dependency. Default `true`. |
| `dependencies` | No | Extra ModIDs added to `ModDependencies` and `LoadAfterIds`. |
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

Each module uses:

- 1 GUID for the hide trigger;
- 1 GUID per show session for the normal restore;
- 1 GUID per show session for the creative restore, when creative restore is on.

With five vanilla sessions, one module uses 11 GUIDs. Two modules use 22. The generator checks that no trigger GUID is also an item GUID.

Use a free block in your own GUID range. The examples set this to `null` on purpose because the toolkit does not own a range. The generator stops with an error until you fill it, or pass `--guid-base` on the command line. The generator cannot check a band against vanilla or against other installed mods.

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

`menugate.config.json` is a record of the inputs and the allocated GUIDs. The game does not read it.

Do not edit the generated files by hand. Change the config or the templates and regenerate.

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
