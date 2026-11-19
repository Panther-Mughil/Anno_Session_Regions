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
- one restore trigger for every show session, with a negated creative-mode subtrigger;
- one creative restore trigger for every show session, with a positive creative-mode subtrigger;
- one generic restore trigger, conditioned on "the active session is not the custom session" with `SessionBlacklist 1`, that also schedules a delayed unlock cue after 500 ms;
- one generic creative restore trigger of the same shape;
- one locked `FeatureUnlock` flag;
- one settle trigger per mode, conditioned on that flag being unlocked.

The shape of one state trigger (the hide and named restore triggers):

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

### The generic restore and the arrival cue

The named restore triggers cover the show sessions in `presets/sessions.json`. A save can also load into a modded session the preset list does not name. A second, generic trigger covers every session the list omits: it uses the same `ConditionActiveSession` template with the custom session GUID plus `<SessionBlacklist>1</SessionBlacklist>`, which means "every session except this one".

The generic trigger also carries an `ActionDelayedActions` with `<ExecutionDelay>500</ExecutionDelay>`. Half a second after the trigger fires, that action unlocks the module's settle flag in whatever session is active then. A separate settle trigger watches the flag with `ConditionUnlocked`; when the delayed action unlocks it, the settle trigger runs the same restore script and then locks the flag again with `ActionLockAsset`, so the cue is one-shot and cannot loop.

The settle trigger has two subtriggers:

- the creative-mode gate, negated for the normal settle and positive for the creative one;
- the same "not the custom session" condition (`ConditionActiveSession` + `SessionBlacklist 1`).

The second guard means a pending cue can never run a restore script inside the custom session. It fires on the next session entry instead.

## 6. The hide script

`hide.lua` runs while the player is in the custom session. It:

1. Force-unlocks the street buildings. This is a safety net; the generator already keeps them out of the item list.
2. Calls `ts.Unlock.SetRelockNet(guid)` for every item in the list.
3. Removes both the normal and the creative restore marker, so the next departure restores again.
4. Writes one runtime log line (`branch=hide`, with the item and failure counts).
5. Returns.

Every item call is wrapped in `pcall`. A failed relock is counted, logged and retried on the next 2 second re-fire; it never stops the remaining items.

`SetRelockNet` changes the game's real unlock state for the player, not a cosmetic UI flag. The `Net` suffix refers to the game's authoritative state. After every item in a tab is locked, the tab has nothing available and the game stops drawing it.

## 7. The show script

`show.lua` runs in every session except the custom one. It does not unlock everything. It asks the game to apply its own unlock rules again.

1. Force-unlock the streets.
2. Read the active session. If it is the custom session, relock the items, clear both markers, log `branch=hide` and return. This is a second line of defence: the trigger condition should already be false there.
3. If a valid marker exists, log `branch=settle` and return. This makes the restore one-shot per visit and absorbs the 500 ms arrival cue.
4. For each item, call `ts.ToolOneDataHelper.GetUnlockTriggerForAsset(guid)`. The answer is the GUID of the trigger that normally grants the item.
5. Collect the distinct trigger GUIDs and call `ts.Conditions.RegisterTriggerForCurrentParticipant(trigger)` for each. Record whether each registration succeeded.
6. Visit every item again:
   - if the lookup raised an error, count a failure and **never** fall through to a direct unlock;
   - if the item has a trigger, count success only when that trigger was registered by this run;
   - if the item has no trigger, unlock it directly with `ts.Unlock.SetUnlockNet(guid)`.
7. Write the marker only when every item succeeded.
8. Log `branch=restore` with `via=named` or `via=generic`, the item count, the success count and the failure count.

The difference from a snapshot restore matters. Reading `GetIsUnlocked` reports the game's default state, not what the player earned. A snapshot restore gave a fresh save most of the menu. Re-registering the triggers restores the rules, so progression decides the result.

The Lua wraps each call in `pcall`. A failed lookup is a failure, not an excuse to grant the item. A partial restore writes no marker, so the next visit retries it.

## 8. The creative script

Creative mode has no progression. The game also turns off progression triggers there, so re-registering them does nothing. `creative.lua` handles that case:

1. Force-unlock the streets.
2. Read the active session. Inside the custom session it relocks the items, removes the creative marker and returns.
3. If a valid creative marker exists, return. This makes the creative restore one-shot per visit; without it the trigger would re-issue every direct unlock every 2 seconds.
4. Otherwise unlock every item directly with `ts.Unlock.SetUnlockNet(guid)`.
5. Write the creative marker only when every item succeeded, and log `branch=creative`.

There is nothing to cheat in creative, so direct unlock is correct.

The normal and creative restore triggers are separated by a `SubTriggers` block with `ConditionIsCreativeMode`:

- The normal trigger negates the condition, so it runs outside creative.
- The creative trigger requires the condition, so it runs only in creative.

The generic restore and the settle trigger each have a creative twin for the same reason.

## 9. Markers and the runtime log

### Markers

The marker paths are `logs/<prefix>_<module>.restore` (normal) and `logs/<prefix>_<module>.restore_creative` (creative), relative to the game's working folder.

A marker is written in the v2 format:

```
v2|<ident>|<item count>|<os.time>
```

- It is written only when **every** item succeeded. A partial restore leaves no marker, so the next visit retries.
- A marker is accepted only when its signature (`<ident>|<item count>`) matches the running script and it is younger than `marker_max_age_seconds` (default 6 hours, 21600).
- Empty, garbled, foreign and stale markers are treated as absent.
- The hide script removes both markers. If a removal fails, it logs the failure and overwrites the marker with an invalidated stamp (`invalidated|0`), so a marker that survives a failed removal can never latch a restore off forever.

The cycle is: leave the custom session, restore once, mark it; enter the custom session, hide and clear the marks; leave again, restore again. Without the marker, the restore trigger would re-register every trigger every 2 seconds.

### The runtime log

Every generated script writes one line per state change to `logs/<prefix>.log` next to the game's other logs. Rotation keeps one backup:

| File | Purpose |
|---|---|
| `logs/<prefix>.log` | The live log. |
| `logs/<prefix>.prev.log` | The previous log, after rotation at `log_rotate_bytes` (default 256 KB). |
| `logs/<prefix>.cursor` | Per-key dedupe state, rewritten through a temp file and renamed into place. |
| `logs/menugate_debug.off` | Create this file to silence the log. |

The log rotates by renaming the live file over the backup; if the backup cannot be replaced it is removed and the rename retried. The cursor keeps one line per distinct key, so two modules alternating every 2 seconds do not overwrite each other's dedupe state.

An identical line is skipped inside `log_dedupe_seconds` (default 60). The dedupe key is:

```
<ident>|<session>|<branch>|<marker>|failed=<n>
```

The failed count is part of the key, so a successful hide never masks a failed one. With no clock, dedupe is skipped entirely and every state change is written.

The line format is:

```
<UTC stamp> | <ident> | session=<guid>(<name>) | [region=<guid>(<name)> |] branch=<hide|restore|creative|settle> | via=<hide|named|generic|settle> | marker=<present|absent|none> | items=<n> | ok=<n> | failed=<n> [| fail=<guid>:<error> ...]
```

The `region=` field appears only when `known_sessions` gives that session a region. At most five failures are printed; more are replaced by `...`. Every `io` and `os` call runs inside `pcall(function() ... end)`, so a missing file API cannot break the gate. Logging is display only: it never changes an unlock.

## 10. Streets

The two New World streets are `101308` (Simple Street) and `101309` (Fast Street). They live inside the Jornaleros and Obreros tabs and the game keeps them available.

The gate cannot both lock and keep a building available. If it locks the streets, the player cannot build roads in the custom session. If it leaves them available, the tab that contains them stays visible.

Unlock state belongs to the player, not the session. The scripts change it when the session changes, but a building that must stay available all the time cannot take part in that change.

Streets Unified moves each region's streets into a separate Streets tab and keeps them unlocked. The tier tabs no longer contain a building that must stay available, so the gate can lock them completely. The gate never locks the Streets tab.

The per-region IDs are in `companions/README.md` and `docs/streets_unified.md`.

## 11. Modules

A module is one item list with its own Lua files and triggers. The core module covers the base game. Each compatibility module covers one group of mods.

Modules are independent by design. The core module does not change when a compatibility module is added, and a problem in one module does not stop the others.

Trigger GUIDs are allocated in order from `trigger_guid_base`. Each module uses, with `N` show sessions:

- 1 hide trigger;
- `N` named restore triggers and `N` named creative triggers;
- 1 generic restore trigger and 1 generic creative trigger;
- 1 settle flag, 1 settle trigger and 1 creative settle trigger.

That is `2N + 6` with creative restore on, or `N + 4` with it off. With the default five show sessions, one module uses **16** GUIDs (9 without creative). Two modules use 32 (18 without creative). The New World demo has four show sessions, so it uses 14 (8 without creative).

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

The trigger is registered when the save loads. The session condition is checked every 2 seconds, so the state settles whichever session the save opens into. The generic trigger and the 500 ms arrival cue cover a load into a session the preset list does not name.

The hide script and the show script are idempotent. Running the hide twice locks the same items twice. Running the show twice returns at the marker. A partial restore writes no marker and is retried. A crash or a reload does not leave the menu in a half state that cannot recover.

## 14. What the gate does not do

- It does not create the session, the map, or the population.
- It does not hide the host region's non-tier tabs. Harbor, ornaments, and similar tabs still appear in the custom session.
- It does not change products, needs, or buildings.
- It does not use a snapshot restore.
- It does not read `mod-loader.log`.
- It does not coordinate two players in different sessions. In co-op, a partner inside the custom session wants the tabs locked while a partner outside it wants them unlocked. The `Net` calls change one shared unlock state, so the last writer wins. Multiplayer is accepted as a known limitation and is not fixed.

## 15. What is tested and what is not

Tested in game:

- The New World gate in normal and creative saves.
- The Streets Unified split for all four regions.
- The trigger and script mechanism described above.

Not tested in game yet:

- The Old World, Arctic, and Enbesa presets.
- The scanner against a wide range of published mods.
- Multiplayer and co-op. The `Net` calls change a shared unlock state, so partners in different sessions request opposite lock states and the last writer wins. This is a known limitation, accepted rather than fixed.

The local test suite checks XML shape, Lua syntax, item counts, generator determinism, preset data, scanner behaviour on fixture mods, and repository hygiene. It cannot check what the game does. An in-game report is the only proof for a new region.
