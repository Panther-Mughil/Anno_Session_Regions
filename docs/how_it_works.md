# How the gate works

This document explains the whole mechanism with the New World as the example. It assumes the custom session is inside the New World region and that Streets Unified is installed.

## 1. The problem

Anno 1800 builds the construction menu from the region. The menu asset `25000035` has one node per region under `Values/ConstructionMenu/RegionMenu`. The New World node is called `Colony01`. Its tier tabs are:

| Tab | GUID | Workforce |
|---|---|---|
| Jornaleros | 25000193 | Jornaleros |
| Obreros | 25000194 | Obreros |
| Artistas | 5466 | Artistas |

A custom session inside the New World inherits that node. The player sees the three New World tabs even though the custom session is meant to have its own content.

The same applies to the other host regions. The Old World node is `Moderate`, the Arctic node is `Arctic`, and the Enbesa node is `Africa`.

## 2. The rule the gate uses

A tab is visible when at least one building inside it is available.

There is no "hide this tab" flag. The project tested the obvious alternatives:

- Locking the tab's `ConstructionCategory` left the tab visible with all its items.
- Locking the population level did not hide the tab. `GetIsUnlocked` returned false for levels even when the tab was shown.
- A wildcard lock does not exist. Every call takes one GUID.

Locking every building inside the tab does hide it. That is the rule the gate is built on, and it has a second half: one available building keeps the tab visible.

## 3. The item list

`src/extract_tier_menu.py` reads the game's `assets.xml` and walks each tier tab. It writes three groups:

- `leaves`: buildings that appear in the tab.
- `containers`: nested `ConstructionCategory` submenus inside the tab.
- `tabs`: the tab categories themselves.

For the New World the raw list has 101 leaves (99 buildings and the two streets `101308` and `101309`), 8 nested submenus, and 3 tabs, for 112 entries. The generator removes the two streets, leaving 110 items to lock.

The nested submenus are included because a submenu can also remain visible when one of its children is available. Locking the buildings and the submenu categories covers both levels.

## 4. The generated mod

`src/generate.py` writes a small mod folder:

```
modinfo.json
data/config/export/main/asset/assets.xml
data/script/<prefix>_<module>_hide.lua
data/script/<prefix>_<module>_show.lua
data/script/<prefix>_<module>_creative.lua
menugate.config.json
```

`menugate.config.json` records the region, the sessions, the item counts, the trigger GUIDs, and a hash of the inputs. It is not read by the game. It exists so a generated folder can be traced back to the config that made it.

The generated `modinfo.json` lists `Streets_Unified` in `ModDependencies` and `LoadAfterIds`. The loader warns if the companion is missing and loads it first.

## 5. The trigger

An XML trigger cannot run logic. It can say "when this condition holds, run this script". The Lua script cannot know when to run. The two pieces are split:

- The trigger is the alarm clock.
- The Lua script is the worker.

Each module gets:

- one hide trigger for the custom session;
- one restore trigger for every other session, with a negated creative-mode subtrigger;
- one creative trigger for every other session, with a positive creative-mode subtrigger.

The shape of one trigger:

```xml
<ModOp Type="addNextSibling" GUID="130248">
  <Asset>
    <Template>Trigger</Template>
    <Values>
      <Standard><GUID>900000100</GUID><Name>Hide Base game in My Custom Session</Name></Standard>
      <Trigger>
        <TriggerCondition>
          <Template>ConditionActiveSession</Template>
          <Values>
            <Condition />
            <ConditionActiveSession><ActiveSession>900000001</ActiveSession></ConditionActiveSession>
          </Values>
        </TriggerCondition>
        <TriggerActions>
          <Item>
            <TriggerAction>
              <Template>ActionExecuteScript</Template>
              <Values>
                <Action />
                <ActionExecuteScript><ScriptFileName>data/script/my_gate_core_hide.lua</ScriptFileName></ActionExecuteScript>
              </Values>
            </TriggerAction>
          </Item>
        </TriggerActions>
        <ResetTrigger>
          <Template>AutoCreateTrigger</Template>
          <Values>
            <Trigger>
              <TriggerCondition>
                <Template>ConditionTimer</Template>
                <Values><Condition /><ConditionTimer><TimeLimit>2000</TimeLimit></ConditionTimer></Values>
              </TriggerCondition>
            </Trigger>
          </Values>
        </ResetTrigger>
      </Trigger>
      <TriggerSetup><AutoRegisterTrigger>1</AutoRegisterTrigger></TriggerSetup>
    </Values>
  </Asset>
</ModOp>
```

The parts:

- `addNextSibling` on `130248` adds the trigger next to a vanilla trigger. The target is a container, not a behaviour.
- `ConditionActiveSession` with the custom session GUID holds true for as long as the player is in that session.
- `ActionExecuteScript` runs a Lua file from `data/script/`.
- `ResetTrigger` with a 2 second timer makes the trigger run again every 2 seconds while the condition holds. The condition is the important part; the timer keeps re-checking it.
- `AutoRegisterTrigger` registers the trigger when the save loads.

The 2 second check solves two cases:

- A save that loads directly into the custom session.
- A save made before the mod existed.

An early version used the `SessionEnter` event. That event fires once, so it never ran on those saves, and the tabs stayed visible. `ConditionActiveSession` is a level condition, so it is true whenever the session is active.

## 6. The hide script

`hide.lua` runs while the player is in the custom session. It does four things:

1. Force-unlock the street buildings. This is a safety net; the generator already keeps them out of the item list.
2. For every item in the list, call `ts.Unlock.SetRelockNet(guid)`.
3. Delete the restore marker.
4. Return.

`SetRelockNet` changes the game's real unlock state for the player, not a cosmetic UI flag. The `Net` suffix refers to the game's authoritative state. After every item in a tab is locked, the tab has nothing available and the game stops drawing it.

## 7. The show script

`show.lua` runs in every session except the custom one. It does not unlock everything. It asks the game to apply its own unlock rules again.

1. Force-unlock the streets.
2. If the marker file exists, return. This makes the restore one-shot per visit.
3. For each item, call `ts.ToolOneDataHelper.GetUnlockTriggerForAsset(guid)`. The answer is the GUID of the trigger that normally grants the item.
4. Collect the distinct trigger GUIDs in a table.
5. For each trigger, call `ts.Conditions.RegisterTriggerForCurrentParticipant(trigger)`. The game then applies that rule to the player again and unlocks only what the player qualifies for.
6. Items that have no trigger are unlocked directly with `ts.Unlock.SetUnlockNet(guid)`.
7. Write the marker file.

The difference from a snapshot restore matters. Reading `GetIsUnlocked` reports the game's default state, not what the player earned. A snapshot restore gave a fresh save most of the menu. Re-registering the triggers restores the rules, so progression decides the result.

The Lua wraps each call in `pcall`. If one call fails, the loop continues and the rest of the menu is still handled.

## 8. The creative script

Creative mode has no progression. The game also turns off progression triggers there, so re-registering them does nothing. `creative.lua` handles that case:

1. Force-unlock the streets.
2. For every item, call `ts.Unlock.SetUnlockNet(guid)`.

There is nothing to cheat in creative, so direct unlock is correct.

The show trigger and the creative trigger are separated by a `SubTriggers` block with `ConditionIsCreativeMode`:

- The show trigger negates the condition, so it runs outside creative.
- The creative trigger requires the condition, so it runs only in creative.

## 9. The marker file

The marker path is `logs/<prefix>_<module>.restore`, relative to the game's working folder.

- The show script writes it after a restore.
- The show script returns early if it already exists.
- The hide script deletes it.

The cycle is: leave the custom session, restore once, mark it; enter the custom session, hide and clear the mark; leave again, restore again. Without the marker, the show trigger would re-register every trigger every 2 seconds.

## 10. Streets

The two New World streets are `101308` (Simple Street) and `101309` (Fast Street). They live inside the Jornaleros and Obreros tabs and the game keeps them available.

The gate cannot both lock and keep a building available. If it locks the streets, the player cannot build roads in the custom session. If it leaves them available, the tab that contains them stays visible.

Unlock state belongs to the player, not the session. The scripts change it when the session changes, but a building that must stay available all the time cannot take part in that change.

Streets Unified moves each region's streets into a separate Streets tab and keeps them unlocked. The tier tabs no longer contain a building that must stay available, so the gate can lock them completely. The gate never locks the Streets tab.

The per-region IDs are in `companions/README.md` and `docs/streets_unified.md`.

## 11. Modules

A module is one item list with its own Lua files and triggers. The core module covers the base game. Each compatibility module covers one group of mods.

Modules are independent by design. The core module does not change when a compatibility module is added, and a problem in one module does not stop the others.

Trigger GUIDs are allocated in order from `trigger_guid_base`. Each module uses one hide GUID, one show GUID per other session, and one creative GUID per other session. With five vanilla sessions, one module uses eleven GUIDs.

## 12. Mod-added items

A mod can add a building to a vanilla tier tab. The core list does not contain that building, so it stays available and the tab reappears with one item.

`src/scan_mods.py` finds those additions and writes a compatibility list. The scanner:

1. Finds mod folders in the three places the loader scans.
2. Reads each `modinfo.json`.
3. Skips disabled mods unless asked to include them.
4. Keeps the higher version when the same ModID appears twice.
5. Reads each mod's XML and classifies its menu edits:
   - a building added inside a tier tab or a nested submenu is included in the list;
   - a category added as a sibling of the tier tabs is a new tab, reported but not locked;
   - a removal is reported but needs no lock.
6. Expands mod-defined categories recursively and uses the vanilla data to expand nested vanilla categories when `--assets` is given.

Then `generate.py --compat` adds a compatibility module.

The scanner is experimental. It understands the common ModOp forms and warns when it cannot follow a mod. The failure direction is asymmetric: an item it misses stays visible in the custom session, while an item it includes that is not in the menu has no effect. The report lists every item and its source mod. A manual entry can be added to the config.

## 13. Loading and saving

The trigger is registered when the save loads. The session condition is checked every 2 seconds, so the state settles whichever session the save opens into.

The hide script and the show script are idempotent. Running the hide twice locks the same items twice. Running the show twice returns at the marker. A crash or a reload does not leave the menu in a half state that cannot recover.

## 14. What the gate does not do

- It does not create the session, the map, or the population.
- It does not hide the host region's non-tier tabs. Harbor, ornaments, and similar tabs still appear in the custom session.
- It does not change products, needs, or buildings.
- It does not use a snapshot restore.
- It does not read `mod-loader.log`.

## 15. What is tested and what is not

Tested in game:

- The New World gate in normal and creative saves.
- The Streets Unified split for all four regions.
- The trigger and script mechanism described above.

Not tested in game yet:

- The Old World, Arctic, and Enbesa presets.
- The scanner against a wide range of published mods.
- Multiplayer. The `Net` calls suggest the state is shared, but this project has not checked how another player's menu behaves.

The local test suite checks XML shape, Lua syntax, item counts, generator determinism, preset data, scanner behaviour on fixture mods, and repository hygiene. It cannot check what the game does. An in-game report is the only proof for a new region.
