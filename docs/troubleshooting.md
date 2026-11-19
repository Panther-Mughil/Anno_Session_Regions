# Troubleshooting

Start with the loader log. It is written to `Documents/Anno 1800/log/mod-loader.log` inside the Windows or Wine user folder. It shows which mods loaded, from which folder, and any XML errors.

XML changes need a game restart. Lua files in `data/script/` are read each time the trigger runs, so a script edit can apply within a few seconds.

## The runtime log

Every generated script writes to `logs/<prefix>.log` relative to the game's working folder (the install folder, whose `logs/` directory already exists). It rotates to `logs/<prefix>.prev.log` at 256 KB and keeps one backup. The dedupe cursor is `logs/<prefix>.cursor`.

Create `logs/menugate_debug.off` to silence it. The path is fixed, not derived from `marker_dir`.

A line looks like this:

```
2026-11-20 09:14:02 | my_gate_core_show | session=180025(New World) | branch=restore | via=named | marker=absent | items=110 | ok=110 | failed=0
```

Fields in order: UTC time, script ident, session GUID with its label, an optional `region=`, `branch` (`hide`, `restore`, `creative` or `settle`), `via` (`hide`, `named`, `generic` or `settle`), the marker state (`present`, `absent` or `none`), the item count, the success count, and the failure count. Up to five failures follow as `fail=<guid>:<error>`.

An identical line is suppressed for 60 seconds, and the failure count is part of the dedupe key. If the log has no timestamps or never appears, the file API is unavailable in that game build; the gate still runs.

## The host tabs are still visible in the custom session

Check these in order:

1. The hide session GUID in the config matches the session asset your mod defines. A wrong GUID means the hide trigger never runs.
2. Streets Unified is installed. Without it, the street buildings stay inside the host tier tabs. The gate keeps them unlocked as a safety net, and one available street keeps the tab visible.
3. A mod adds buildings to the host tier tabs. Run `scan_mods.py`, generate with `--compat`, and restart.
4. The tab contains a nested submenu or a DLC tier that is not in the item list. Compare the tab against `presets/items/<region>_core.json`.
5. The trigger is registered. Open the loader log and check that the gate's XML loaded without errors. Missing `modinfo.json` dependencies also stop the gate from applying.

## The tabs are hidden everywhere

1. The hide trigger is using a session GUID that matches more than you expect. Check `hide_session.guid`.
2. The show triggers did not load. Check the gate's XML in the loader log.
3. A marker file from an earlier attempt is still present. Delete `logs/<prefix>_<module>.restore` and `logs/<prefix>_<module>.restore_creative` in the game's working folder and change session once. The hide script normally deletes them. A marker is also ignored when its signature does not match the current item count or when it is older than `marker_max_age_seconds` (6 hours by default), so a stale one expires on its own.

## Roads are missing in the custom session

1. Check that Streets Unified loaded.
2. Check that the generated hide script force-unlocks the street IDs at the top. The generator adds them from the preset.
3. If you replaced the module's `keep_unlocked` list, put the street IDs back.

## The restore gives the player everything

The show script unlocks items that have no unlock trigger directly. That is correct for items the game treats as always available. If a vanilla item is normally locked by a population rule, it should have a trigger, and the script re-registers that trigger instead.

If everything is unlocked, check that the show script is the one running and not the creative script. The creative script unlocks every item by design. The show trigger has a negated `ConditionIsCreativeMode` subtrigger; the creative trigger has a positive one.

A snapshot restore is not used. If you added one by hand, remove it.

## The restore gives too little, or the normal menu is empty

1. The show script may not be running. Check the session GUIDs in the show triggers. They must list every session except the hide session.
2. The marker may be blocking the restore. Delete `logs/<prefix>_<module>.restore` and change session. A marker is written only when every item succeeded, so a partial restore retries on its own.
3. The game may have saved while the items were locked. Enter the host session, let the show trigger run, and wait 2 seconds.
4. The generic restore or its 500 ms arrival cue did not fire in a modded session. Check the loader log for the trigger assets, and confirm the session GUID in `hide_session` is correct; the generic trigger is conditioned on "not this session".
4. A compatibility module may be locking an item that belongs to the host session. Check `compat.json` and remove the entry if the scanner over-included it.

## Creative mode behaves differently

Creative mode turns off progression triggers in the game. The gate mirrors that with two separate scripts. In creative, the creative script unlocks the items directly outside the custom session. In the custom session, the hide script still locks them.

If creative shows the host tabs in the custom session, the hide trigger is not running. Check the session GUID.

## A mod-added tab is visible in the custom session

The gate hides the base game tier tabs. A mod tab added next to them is a separate tab and is not in the core list. The scanner reports it under `new_tabs`.

To hide it, add a module with the tab's contents:

```json
{
  "key": "extra_tab",
  "name": "Example mod tab",
  "items": [123456, 123457, 123458]
}
```

Use the item list from the mod's category asset. The module gets its own hide and restore triggers.

## The generator says trigger_guid_base is empty

That is deliberate. Open the config and set `trigger_guid_base` to the first free GUID in your own range, or pass `--guid-base 2001202271` on the command line. The examples leave it empty because the toolkit cannot know your range. See `docs/configuration.md`.

## The scanner finds no mods

1. Run `python src/scan_mods.py --preset new_world --print-roots`. It prints the folders it checked.
2. On Linux, pass `--game-dir` for the install. The game can be on any mount.
3. The loader follows symlinks, and the scanner does too. Check that the mods folder itself is reachable.
4. Zip mods are not scanned. Extract the folder.

## The scanner misses items

The scanner understands the common ModOp forms. An unusual mod edit can evade it. Add the missing IDs to the module's `items` list and open an issue with the mod name and the report so the scanner can learn the pattern.

## The scanner reports a new tab you expected to be locked

A category inserted as a sibling of the tier tabs is a new tab, not part of a tier tab. The scanner reports it under `new_tabs` and leaves it alone. Add a module by hand if it should be hidden.

## The game shows a construction warning or a blank building

That is usually a mod content problem, not the gate. Check the loader log for an XML error and remove the mod that owns the building. The gate only changes unlock state; it does not create or edit buildings.

## Multiplayer and co-op

The gate has not been tested in multiplayer. This is a **known limitation, accepted rather than fixed**.

The `Net` calls change one shared unlock state. In co-op, partners in different sessions request opposite states: the partner inside the custom session wants the tabs locked, while the partner outside it wants them unlocked. The scripts are client-local, so the last session change wins and both players see that result. Do not expect per-player menus in co-op. A single-player or shared-session game behaves as described above.

## Approaches that do not work

These were tried and did not work. Do not spend time on them.

- Locking a `ConstructionCategory`. The tab stayed visible with all its items.
- Locking population levels. The tabs stayed visible, and `GetIsUnlocked` returned false for levels even when a tab was shown.
- Restoring from a snapshot of `GetIsUnlocked`. It reports default state, not earned progress, and over-unlocked a fresh save.
- A wildcard lock. No such call exists.
- Discovering mods at runtime with `ts.GetModInfo()` or `ts.GetMods()`. Both return empty.
- Editing the game executable to load mods. GU17 and newer have a loader in the game.
- Using `mod-loader.log` as the source for the compatibility list. It only describes the last launch.

## What to include in a bug report

- Game version, for example GU18.4.
- Host region and the custom session GUID.
- The generated config and `compat.json` if you used the scanner.
- The loader log.
- The steps that show the problem, and whether it happens in a new save, a loaded save, normal mode, or creative.
- A screenshot of the menu if the problem is visual.

The issue template asks for these. A clear report with the files attached is more useful than a description alone.
