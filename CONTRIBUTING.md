# Contributing

Thanks for helping. This project is for the Anno 1800 modding community, and reports from people testing the untested regions are as useful as code changes.

## Ways to contribute

- Report a bug or a region test result.
- Improve the documentation.
- Add a host region preset.
- Improve the scanner for a ModOp pattern it misses.
- Translate the guide. The project is written in English; a translation can live in `docs/` with a language suffix.
- Fix a typo or a broken link.

## Before opening an issue

1. Read `docs/troubleshooting.md`.
2. Search the existing issues. Someone may already have reported it.
3. Try the latest release. Only the latest version is supported.

## Bug reports

Use the bug report template. It asks for:

- the game version;
- the host region and custom session GUID;
- what you expected and what happened;
- the steps to reproduce;
- whether it happens in a new save, a loaded save, normal mode, or creative;
- the generated config and compatibility list if you used the scanner;
- the loader log;
- a screenshot if the problem is visual.

You do not need to be a programmer to report a bug. The files matter more than the wording.

## Region test reports

The Old World, Arctic, and Enbesa presets have not been tested in game. If you test one, open an issue with the region, the game version, and the result. Say whether the host tabs were hidden in the custom session and whether they returned when you left. A report with no bug is still useful.

## Feature requests

Open an issue with the problem you want to solve and the outcome you want. Say which host region and mods are involved. If the request changes the generated output or the config format, mention it so the versioning can be planned.

## Pull requests

1. Fork the repository and create a branch.
2. Keep the change focused. One topic per pull request.
3. Add or update tests.
4. Run the suite:

   ```sh
   python -m pytest
   ```

5. Update the documentation if the change is user-visible.
6. Add an entry to `CHANGELOG.md` under `Unreleased`.
7. Fill in the pull request template.

### What not to include

- Game assets, extracted vanilla files, or game executables.
- Content from a private mod or another author's mod without permission.
- Personal paths, private GUID bands, or account names.
- Generated output that the tools can rebuild. Commit the config or the fixture, not the output.

### Code style

- Python 3.10 or newer.
- Standard library for the shipped tools.
- Type hints on public functions.
- Short command line output; detailed data goes in the JSON report.
- Tests must run without a game install.

## Commit messages

Write what changed and why in the subject. A short body is welcome for anything that is not obvious. Use the imperative mood, for example "Fix the scanner symlink walk".

## Code of conduct

Participation is covered by `CODE_OF_CONDUCT.md`. Be direct about the work and respectful to the people.

## License

By contributing, you agree that your contribution is released under the MIT license used by the project. You keep the copyright to your work, and the project keeps the license text with the distribution.
