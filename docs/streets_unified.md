# Streets Unified and the street problem

Streets Unified is a required companion mod. It is included in `companions/streets_unified` and released under the same MIT license.

## The conflict

The gate hides a tier tab by locking every building inside it. Streets are buildings inside the tier tabs, and the game keeps them available at all times. That produces two bad choices:

- Lock the streets with the rest of the tab. The tab hides, but the player cannot build roads in the custom session.
- Leave the streets available. Roads work, but one available building keeps the whole tab visible. The player sees the host tab with only roads in it.

The same street cannot be locked in the custom session and unlocked in the host session. Unlock state belongs to the player, not to the session. The scripts change it when the session changes, so any building that must stay available all the time cannot take part in the change.

## The fix

Streets Unified gives each region its own Streets tab and moves the street buildings into it:

| Region | Menu node | Street buildings | Streets tab |
|---|---|---|---|
| Old World | Moderate | 1000178, 1010035 | 2001229950 |
| New World | Colony01 | 101308, 101309 | 2001229951 |
| Enbesa | Africa | 114523, 119029 | 2001229952 |
| Arctic | Arctic | 112113 | 2001229953 |

It also:

- removes those buildings from the host tier tabs;
- inserts the Streets tab next to the tier tabs;
- adds trigger `2001229954`, which unlocks every street building in every session.

The gate never locks the Streets tab. Roads stay available in the custom session, and the tier tabs no longer contain a building that must stay available.

## Installing

Copy `companions/streets_unified` into the game's mods folder next to the generated gate. Install one copy only. If you already have the original Streets Unified, do not install both; the loader deduplicates by ModID and keeps one, which makes updates confusing.

The generated `modinfo.json` already contains:

```json
"ModDependencies": ["Streets_Unified"],
"LoadAfterIds": ["Streets_Unified"]
```

The loader warns if the companion is missing and loads it before the gate. Do not merge the companion into the gate folder. Keep it as its own mod.

## If Streets Unified is missing

The generator still keeps the street IDs out of the lock list and force-unlocks them in every script. Roads keep working, but the street buildings stay inside the host tier tabs. The tab then has one available building, so it stays visible. The gate cannot hide that tab.

The loader warning is the sign that the companion is missing. Install it and restart the game.

## If the Streets tab is missing in game

1. Check that `streets_unified` is in the mods folder and enabled.
2. Check the loader log for `Streets_Unified`.
3. Check that the gate's `modinfo.json` lists it in `ModDependencies` and `LoadAfterIds`.
4. Restart the game. XML changes are not read live.

## If streets are duplicated

Two copies of the mod, or another mod that also edits the same tier categories, can leave a street in both places. Remove the duplicate copy. The loader deduplicates by ModID and keeps the higher version, so two folders with the same ModID produce a version warning rather than a second copy, but two different ModIDs that both move streets can overlap.

## Why not avoid the extra mod

The alternative is to break one of the rules:

- Keep the streets in the tier tabs and accept that the host tab stays visible in the custom session.
- Lock the streets and accept that roads are unavailable in the custom session.
- Change unlock state per session with a snapshot, which over-unlocks saves and is the approach this project rejects.

A separate tab keeps roads available and keeps the tier tabs empty. It costs one extra mod.
