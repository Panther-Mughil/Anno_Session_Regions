# Roadmap

These are the next pieces of work. They are plans, not promises. If one of them matters to your mod, open an issue with the use case.

| Status | Item |
|---|---|
| **Planned** | Suppress notification toasts when unlocking items. |
| **Planned** | Find better ways to merge streets back into the building tabs. |
| **Planned** | Add compatibility discovery with more mods. |
| **Done in 0.1.0-alpha.7** | Compatibility with other modded sessions, through the generic restore. |

## Suppress notification toasts

The gate locks and unlocks a large list of items when the session changes. The game may show unlock toasts for them. The goal is to find a quiet path that does not change the unlock state.

**Done when:** entering and leaving the custom session does not spam the player with toasts, in normal and creative mode.

## Merge streets back into the building tabs

Streets Unified moves each region's streets into their own tab. That is what lets the gate empty the host tier tabs. Some modders would prefer the streets to stay in the normal building tabs.

**Done when:** streets are available in the host tabs without keeping a host tier tab visible in the custom session.

## Compatibility discovery with more mods

The scanner knows the common ModOp forms. Published mods use more patterns. The goal is to add fixture cases, test against more published mods, and report what still cannot be followed.

**Done when:** the scanner has fixtures for the common published-mod patterns and its report is reliable on a broad mod list.

## Compatibility with other modded sessions

Two mods can add sessions or gates. Their triggers, load order, and GUID blocks can overlap.

**Done in 0.1.0-alpha.7.** A save that loads into a modded session the preset list does not name is covered by the generic restore: `ConditionActiveSession` on the hidden session with `SessionBlacklist 1`, plus a 500 ms arrival cue and a one-shot settle trigger. The trigger GUID collision check stops a gate from reusing an item GUID, and `--compat` gives each group of installed mods its own module. An in-game report from another session mod is still welcome.

## Suggest a roadmap item

Open a feature request and describe the problem, the host region, and the mods involved. A clear use case moves an item forward.
