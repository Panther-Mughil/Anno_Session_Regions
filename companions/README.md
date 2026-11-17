# Streets Unified

This folder is a separate mod. The menu gate depends on it, so install it next to the gate in the game's mods folder.

## Why it is required

Streets are buildings inside the host region's tier tabs, and the game keeps them unlocked at all times. The gate hides a tier tab by locking every building in it. That creates a problem with streets:

- Lock them with the rest of the tab and the player cannot build roads in the custom session.
- Leave them unlocked and one available building keeps the whole tab visible, which defeats the gate.

The same street cannot be locked in one session and unlocked in another, because unlock state belongs to the player. The scripts flip that state when the session changes, and a building that must always be available cannot take part in the flip.

Streets Unified solves this by giving each region a separate Streets tab:

| Region | Street buildings moved | Streets tab |
|---|---|---|
| Old World | 1000178, 1010035 | 2001229950 |
| New World | 101308, 101309 | 2001229951 |
| Enbesa | 114523, 119029 | 2001229952 |
| Arctic | 112113 | 2001229953 |

It also removes those buildings from the host tier tabs and adds a trigger (2001229954) that unlocks them in every session. The gate never locks that tab, so roads stay available in the custom session and the tier tabs can be emptied completely.

## Installing

Copy the `streets_unified` folder into the game's mods folder. Install one copy only. If you already have the original Streets Unified, do not install both; the loader deduplicates by ModID and keeps one.

It must load before the gate; the generated `modinfo.json` already lists it in `ModDependencies` and `LoadAfterIds`, so the loader orders it correctly and warns if it is missing.

Do not merge this folder into the generated gate. Keep it as its own mod.

## Credit and license

Streets Unified is by Panther and is part of this project. It is released under the same MIT license as the rest of the repository.
