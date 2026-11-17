# Supported host regions

The gate works for a custom session inside any of the four vanilla regions. Each preset records the menu node, the tier tabs, the street buildings, and the host sessions.

Pick one preset per gate. A mod for one region needs one config. The other presets are alternatives, not required steps. If you build gates for several regions, give each one its own mod ID and trigger GUID base.

## The four presets

| Region | Preset | Menu node | Tier tabs | Items to lock | In-game test |
|---|---|---|---|---|---|
| New World | `new_world` | Colony01 | 3 | 110 | Yes |
| Old World | `old_world` | Moderate | 7 | 148 | Not yet |
| Arctic | `arctic` | Arctic | 2 | 35 | Not yet |
| Enbesa | `enbesa` | Africa | 2 | 63 | Not yet |

The item counts are after the street buildings are moved to the keep-unlocked list. The raw lists and the per-tab counts are in `presets/items/<region>_core.json`.

## New World

| Tab | GUID | Workforce |
|---|---|---|
| Jornaleros | 25000193 | Jornaleros |
| Obreros | 25000194 | Obreros |
| Artistas | 5466 | Artistas |

Streets: 101308, 101309. This is the only region with an in-game pass. It has been checked in normal and creative saves.

## Old World

| Tab | GUID | Workforce |
|---|---|---|
| Farmers | 25000189 | Farmers |
| Workers | 25000190 | Workers |
| Artisans | 25000191 | Artisans |
| Engineers | 25000192 | Engineers |
| Tourists | 132779 | Tourists (DLC) |
| Investors | 500447 | Investors |
| Scholars | 502107 | Scholars (DLC) |

Streets: 1000178, 1010035.

Tourists and Scholars need their DLC. On an install without those DLCs their tabs do not exist, and locking their IDs does nothing. That is harmless.

Cape Trelawney is a session inside the Old World region and shares the same menu. A custom session inside Cape Trelawney uses the `old_world` preset. The preset lists Cape Trelawney under `related_sessions` for documentation.

## Arctic

| Tab | GUID | Workforce |
|---|---|---|
| Explorers | 112790 | Explorers |
| Technicians | 112791 | Technicians |

Street: 112113.

The Arctic menu also lists a creative-only Passage category (`10272`). It is not a tier tab and is not in the preset.

## Enbesa

| Tab | GUID | Workforce |
|---|---|---|
| Shepherds | 114553 | Shepherds |
| Elders | 114554 | Elders |

Streets: 114523, 119029.

The Enbesa menu also lists a creative-only Land of Lions category (`10245`). It is not a tier tab and is not in the preset.

## How the item lists were made

The shipped lists were generated from game version GU18.4 with:

```sh
python src/extract_tier_menu.py --assets "/path/to/assets.xml" \
  --preset presets/new_world.json \
  --out presets/items/new_world_core.json
```

The extractor walks the game's own menu data. The tests compare each shipped list with the preset and fail if a count or a street ID stops matching.

## After a game update

1. Run `python src/discover_regions.py --assets "/path/to/assets.xml" --out-dir presets/drafts`.
2. Compare the draft with the shipped preset. The script prints the menu node and the tier tabs it found.
3. If the tabs changed, update the preset and regenerate the item list with `extract_tier_menu.py`.
4. Run the tests.
5. Start the game and check one region before publishing a new release.

`discover_regions.py` fills `host_sessions` and `street_assets` only for the four regions it knows. For a new host region, fill those by hand.

## Adding a host region

A host region is any `RegionMenu` node with tier tabs. The steps:

1. Draft the preset with `discover_regions.py`.
2. Find the street buildings for that region. Streets Unified may already move them; if not, add a region entry to the companion or ship the gate without the street split and document the visible tab.
3. Fill `host_sessions` with the sessions that use the region menu.
4. Generate the item list.
5. Add an example config under `examples/`.
6. Add the region to the test expectations.
7. Ask for an in-game report before marking it tested.

The gate does not care what the region is called. It needs the menu node, the tab IDs, the item list, and the hide session.

## Test status

Only the New World has an in-game pass. The other three presets use the same mechanism and pass the local tests, but a local test cannot prove what the game draws. Treat them as beta until someone reports a result.
