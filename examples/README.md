# Examples

Each folder has a config that the generator can read. The four region configs are templates. They do not hide anything until you replace the placeholder session GUID with the GUID of your own session asset. The demo is the only runnable example.

| Folder | Region | Hide session | Use |
|---|---|---|---|
| `new_world` | New World | 900000001 placeholder | A custom session inside the New World |
| `old_world` | Old World | 900000002 placeholder | A custom session inside the Old World or Cape Trelawney |
| `arctic` | Arctic | 900000003 placeholder | A custom session inside the Arctic |
| `enbesa` | Enbesa | 900000004 placeholder | A custom session inside Enbesa |
| `demo_new_world` | New World | 180025, the real New World | A test only: hides the New World tabs while you are in the New World |

## Run one

```sh
python src/generate.py --config examples/new_world/config.json
```

The output goes to `examples/new_world/out/My_Session_Gate_NewWorld`.

## What to change

Before installing a generated gate, change these fields in the config:

- `hide_session.guid` and `hide_session.name`: your session.
- `mod_id`, `mod_name`, `creator`, and `version`: your mod's values.
- `trigger_guid_base`: the first of the eleven GUIDs the gate will define. The examples leave it `null` on purpose. Fill it with the first free GUID in your own range, or pass `--guid-base`. The generator stops until it is set.
- `script_prefix`: a short prefix for the Lua file names.
- `output`: optional. The default is `out/<mod_id>` next to the config.

Do not reuse the example GUID bands in a published mod. They are placeholders.

## The demo

`demo_new_world` is the only example that works without a custom session. It hides the New World tier tabs while you are in the New World, and restores them when you leave. Install it, enter the New World, and check that the three tier tabs are gone and the Streets tab is still there. Then remove it. It is a test, not a playable configuration.

## Counts

The generated core module locks 110 items for the New World, 148 for the Old World, 35 for the Arctic, and 63 for Enbesa. The item lists are in `presets/items/`.

## Adding the compatibility module

```sh
python src/scan_mods.py --preset new_world --game-dir "/path/to/Anno 1800" --out compat.json
python src/generate.py --config examples/new_world/config.json --compat compat.json
```

The second command adds a `compat` module. The core module does not change.
