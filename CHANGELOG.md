# Changelog

All notable changes to this project are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0-alpha.6] - 2026-11-18

### Changed

- `LICENSE` is the standard MIT text so GitHub detects the license as MIT.
- The credit request lives in `NOTICE`. It asks only for Panther credit.
- The README credit section asks only for Panther credit. The Aveline and Streets Unified lines were removed from that section.
- No gameplay or generator behavior change.

## [0.1.0-alpha.5] - 2026-11-18

### Changed

- CI uses `actions/checkout` v7, `actions/setup-python` v7, `ubuntu-24.04`, and `pytest` 9.2.0 or newer. The Node 20 and `ubuntu-latest` annotations are gone.
- The repository uses branch rulesets for `main`: force pushes and deletion are blocked, and the three CI checks are required.

## [0.1.0-alpha.4] - 2026-11-18

### Added

- The trigger GUID count for one custom session is now in the configuration, step-by-step and AGENTS guides: 11 with one core module and the default settings, 6 without creative, 22 with a compatibility module, and 9 for the New World demo.

### Changed

- This release includes the documentation commit authored by Aveline (AI). There is no gameplay or generator behavior change.

## [0.1.0-alpha.3] - 2026-11-18

### Added

- `docs/step-by-step.md`, a beginner walkthrough with every parameter and every command.
- A visible roadmap in the README and `docs/roadmap.md`.
- `CREDITS.md`, and a bold attribution request in `LICENSE` and the README.
- Aveline (AI) is listed as the AI assistant and commit co-author.

### Changed

- The README was reformatted with tables, bold key terms, and separate Windows and Linux scanner paths.

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
