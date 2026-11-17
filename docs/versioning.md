# Versioning and releases

## Current version

`0.1.0-alpha.3`, tagged `v0.1.0-alpha.3`.

Alpha means:

- The gate mechanism works for the New World and has been checked in game in normal and creative saves.
- The Old World, Arctic, and Enbesa presets pass the local tests but have not been checked in game.
- The compatibility scanner is experimental.
- The command line, config fields, and generated file names may change between minor versions.

## Semantic versioning

The project uses semantic versioning with pre-release labels.

| Change | Version bump |
|---|---|
| A bug fix that keeps the config and generated output compatible | PATCH, for example `0.1.1-alpha.2` |
| A new region, a new tool, or a new config field that does not break existing configs | MINOR, for example `0.2.0-alpha.1` |
| A change that needs an existing config or generated folder to be migrated | MAJOR, for example `1.0.0` |

While the version is below `1.0.0`, a minor bump may still include a small migration. Every release that needs one says so in `CHANGELOG.md`.

The version leaves alpha when all four host regions have had an in-game pass and the scanner has been checked against a reasonable set of published mods.

## Tags

Every release gets a Git tag on the release commit:

```
v0.1.0-alpha.1
v0.1.0-alpha.2
v0.1.0-alpha.3
v0.1.1-alpha.4
v0.2.0-alpha.1
```

The tag and the version in `src/version.py` must match. The test suite refuses a version that is not in the `x.y.z-alpha.n` form.

## Generated output

Every generated file starts with the toolkit version. `menugate.config.json` also records:

- the toolkit version;
- the region and menu node;
- the preset file name;
- the hide and show sessions;
- the module counts and trigger GUIDs;
- the config itself;
- a SHA-256 hash of the resolved inputs.

The hash makes it possible to tell whether two generated folders came from the same inputs. The generated folder does not call the toolkit at runtime.

## Updating a generated gate

1. Keep your config file. It is the source of truth.
2. Read the changelog for the new version.
3. Run the new generator on the same config.
4. If the release note asks for a config change, make it.
5. Compare the new output with the old one. The trigger GUIDs should be stable when the module list and trigger base do not change.
6. Replace the installed folder and restart the game.

Do not edit generated Lua or XML by hand. Regenerate instead.

## Release checklist

1. All tests pass.
2. The four example gates generate without warnings.
3. Lua syntax check passes for every generated script.
4. The item lists match the presets.
5. `CHANGELOG.md` has an entry with the date and the changed files.
6. `src/version.py` and the tag match.
7. The release notes say which regions are tested and which are not.
8. The release archive includes the source, the companion, and the generated examples if they are shipped.
9. The README support table is up to date.

## Support policy

Only the latest release is supported. If a bug exists in an older tag, reproduce it on the latest tag before reporting it.

A report for an untested region is valuable even when nothing is broken. It moves that region from beta to tested and changes the support table.
