# Changelog

All notable changes to this project are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0-alpha.2] - 2026-11-18

### Added

- `--skip-triggers` and `generate_triggers: false`: the generator writes the Lua scripts plus `menugate.triggers.json` and `menugate.triggers.xml.txt` instead of the trigger XML.
- `AGENTS.md`, a step-by-step workflow for an AI coding agent helping a modder.
- Tests for manual trigger mode and for single-region example configs.

### Changed

- The documentation states that one config covers one host region. Generating the other three examples is not required. Multi-region use needs a distinct mod ID and trigger GUID base per config.

## [0.1.0-alpha.1] - 2026-11-18

First public alpha.

### Added

- Session menu gate generator for Anno 1800, with hide, restore, and creative scripts per module.
- Host region presets and generated item lists for the New World, Old World, Arctic, and Enbesa.
- Region discovery tool for drafting presets after a game update.
- Compatibility scanner for installed mods, with duplicate ModID handling, activation handling, symlink support, and source attribution per item.
- Streets Unified companion mod, required by the gate.
- Examples for each region and a New World demo config.
- Documentation: how it works, streets, regions, configuration, compatibility, troubleshooting, versioning, FAQ, and development.
- Test suite covering extraction, generation, presets, the scanner, and repository hygiene.
- GitHub issue templates, pull request template, CI workflow, code of conduct, contribution guide, and security policy.

### Changed

- Example configs leave `trigger_guid_base` empty. The generator stops until a value is filled in or passed with `--guid-base`.
- Each example uses a different placeholder session GUID so copied configs do not collide.

### Fixed

- The generated `modinfo.json` carries all 11 language keys.
- The generator rejects an empty trigger base, an int32 overflow, and warns on a version that is not three numbers.
- Streets Unified categories carry `Text` and `Locked` blocks, and all 11 language text files label the Streets tab.

### Tested

- New World gate in normal and creative saves.

### Not tested yet

- Old World, Arctic, and Enbesa presets in game.
- Compatibility scanner against a wide range of published mods.
- Multiplayer.

### Known issues

- The scanner is experimental. It understands the common ModOp forms and warns when it cannot follow a mod.
- The 2 second reset uses a `TimeLimit` value that does not appear in vanilla trigger assets. The same block is used by the tested gate.
- Zip mods are reported but not scanned.
