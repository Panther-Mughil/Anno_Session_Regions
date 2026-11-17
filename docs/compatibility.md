# Compatibility scanner

`src/scan_mods.py` finds what installed mods add to the host region's tier tabs and writes a compatibility list for `generate.py --compat`.

The scanner is experimental at version 0.1.0. Treat its report as evidence to check, not as a guarantee.

## Where it looks

The loader scans three mod folders:

1. `<game install>/mods`
2. `Documents/Anno 1800/mods` inside the Windows or Wine user folder
3. `C:/users/Public/mod.io/4169/mods`

On Linux, pass `--game-dir` because the install can be on any mount. The scanner checks common Wine, Steam, and Lutris prefixes for the Documents and mod.io folders. Use `--print-roots` to see what it found.

The scanner does not read `mod-loader.log`. The log describes the last launch, misses mods downloaded since, and depends on the log format.

## What it respects

- `activations.json`: the `disabledIds` list at each root.
- The `-` folder prefix, which disables a mod.
- Collections: a folder without `modinfo.json` whose children each have one.
- Components: nested folders with their own `modinfo.json` are scanned as separate mods.
- Duplicate ModIDs: the higher `Version` wins. The loader's exact order between roots is not documented, so a tie produces a warning.
- `.lnk` folder links: followed when the target is a folder.
- `.zip` mods: not scanned. The scanner warns and asks you to extract the folder.

## What it reads

The scanner parses every XML file in an enabled mod, except files inside a nested component that has its own `modinfo.json` (those are scanned as their own mod).

It classifies menu edits by the ModOp type and the path:

| Edit | Result |
|---|---|
| A building added to a tier tab or a nested submenu | Included in `items` |
| A new category added inside a tier tab | Included, with its children expanded |
| A category added as a sibling of the tier tabs | Reported in `new_tabs`, not locked |
| A building or category removed from a tier tab | Reported in `removed`, no lock needed |
| A mod-defined category used by the above | Expanded recursively |
| A nested vanilla category used by the above | Expanded when `--assets` is given |

The distinction between "inside a tab" and "next to the tabs" is the reason the scanner looks at `addNextSibling` and `addPrevSibling`. Those types insert a sibling next to the anchor. A path that anchors on `Item[Category='<tier tab>']` under `Tier/Categories` adds a new tab, not an item inside the tab. Getting that wrong would lock an entire mod tab by accident.

## Why over-inclusion is safe

Locking an asset that is not in the construction menu does nothing. Missing an asset that is in the menu leaves it visible in the custom session. The scanner therefore errs toward including items and reporting anything it cannot place.

## Reading the report

```json
{
  "region": "new_world",
  "region_node": "Colony01",
  "items": [
    {
      "guid": 123456,
      "name": "Example building",
      "source_mod": "Example_Mod",
      "reason": "added inside tier tab 25000194"
    }
  ],
  "new_tabs": [],
  "removed": [],
  "warnings": []
}
```

- `items`: pass this to `generate.py --compat`.
- `new_tabs`: mod tabs that stay visible. Add them by hand if the custom session should hide them.
- `removed`: vanilla items a mod removed. No action is needed.
- `warnings`: duplicate ModIDs, XML parse failures, and edits the scanner could not classify.
- `roots`: the folders that were found and the ones that were missing.
- `mods`: every mod that was scanned, with its enabled state.

## Manual entries

If the scanner misses an item, add it to the module in the config:

```json
{
  "key": "compat",
  "name": "Installed mods and manual fixes",
  "items_file": "compat.json",
  "items": [123456, 123457],
  "keep_unlocked": [101308, 101309]
}
```

`items` is merged with the compatibility list. `keep_unlocked` removes an ID from the lock list and forces it unlocked in every script.

## Limits

- It cannot follow a mod that builds its XML with a non-standard structure.
- It does not scan zip mods.
- It cannot know a mod's runtime behaviour. It reads the files as written.
- It reads the first version of a duplicated ModID, not the one the loader actually chose, when the versions cannot be parsed.
- It reports paths from your machine in the JSON. Remove them before sharing a report in public if you care about folder names.

## Verifying a report

If you want a second opinion, compare the report with `mod-loader.log`. The log confirms which mods loaded and from where. It does not list the merged menu, so it cannot replace the scanner; it can confirm that a mod the scanner missed was loaded at all.
