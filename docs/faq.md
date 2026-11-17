# Frequently asked questions

## Is this a new region?

No. A new region is not moddable in Anno 1800. The project creates a new session inside an existing region and hides that region's tier tabs while the player is in the session. The region keeps its terrain rules, assets, and population data.

## Can I hide more than the tier tabs?

Not with the core module. The gate hides the tier tabs because those contain the host region's production and residence content. Harbor, ornaments, and similar tabs stay visible.

You can add a module with the IDs of another tab's contents. The module uses the same hide and restore mechanism.

## Do I need Streets Unified?

Yes. Without it, the street buildings stay inside the tier tabs. The gate keeps them unlocked so roads work, but one available street keeps the tab visible. The loader warns when the companion is missing.

## Can I use this without Python?

Not today. The tools are Python scripts. Python 3.10 or newer is enough; there are no third-party packages to install for the gate itself. A packaged build could come later.

## Does it change vanilla assets?

The gate adds trigger assets and Lua scripts. It does not replace or edit vanilla buildings. Streets Unified does edit the vanilla construction categories to move the streets into their own tab, and it does so with explicit ModOps.

## Will it break my save?

The gate changes unlock state while the session is active and restores the game's own rules when you leave. It does not write to the save directly. The tested New World gate was used in normal and creative saves without a save failure.

A mod that changes unlock state always carries some risk. Make a backup before testing a new region for the first time.

## Can I uninstall it?

Yes. Remove the gate folder and Streets Unified from the mods folder. If the game is saved while inside the custom session, the vanilla menu may be missing until the show script runs in another session, so leave the session before uninstalling.

If a marker file is left behind, delete `logs/<prefix>_<module>.restore` in the game's working folder.

## Why does the restore re-register triggers instead of unlocking items?

Unlocking every item would give a new player content they never earned. Reading the current unlock state reports the game's defaults, not progress. Re-registering the game's own unlock triggers restores the rules, and the game then decides what the player earned. That is the only approach that kept a fresh save honest.

## Why 2 seconds?

The trigger condition is checked on a timer. The condition itself stays true for the whole session; the timer makes the action run again after a session change. Two seconds is the value used by the tested gate. A shorter value would add calls without changing the result; a longer value makes the menu lag the session change.

## Why does the item list include submenus?

A nested submenu is also a category with its own availability. Locking only the buildings can leave a submenu visible. The list includes the buildings, the nested submenus, and the tab categories.

## Does it work with DLC?

The New World and Arctic presets use base game tabs. The Old World preset includes Tourists and Scholars, which need their DLC. On an install without those DLCs the tabs do not exist, and locking their IDs does nothing.

Enbesa needs its DLC to exist at all. The preset is still valid; on an install without Enbesa the region is simply absent.

## Does it work in multiplayer?

Untested. The scripts use the game's networked unlock calls, so the state is likely shared, but the project has not checked how a second player's menu behaves. Report what you see.

## Why is the scanner experimental?

Mods change the game through small edit instructions, and the scanner supports the common forms. An unusual form can slip past it. The project labels it experimental, reports every item with its source mod, and supports manual entries.

## Can I publish a mod that uses this?

Yes. The license is MIT. Keep the copyright notice and license text with copies of the project. You do not need to publish your mod's source.

## Can I sell a mod that uses this?

The MIT license allows it. Credit is required in the form of the retained copyright notice and license text.

## Is this affiliated with Ubisoft?

No. Anno 1800 is a trademark of Ubisoft. This is an unofficial community project.
