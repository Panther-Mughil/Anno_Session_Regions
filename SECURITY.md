# Security policy

## Supported versions

Only the latest release is supported. The current version is `0.1.0-alpha.2`.

## What counts as a security issue

This project generates Anno 1800 mod files. A security issue is something that can harm a user's machine or data outside the game. Examples:

- A script that writes outside the game's folders.
- A path handling bug that lets a downloaded mod folder write to an unexpected place.
- A command injection in a tool that takes a path.
- A supply chain problem in the release process.

A mod that changes the game's balance, unlocks content, or breaks a save is a bug, not a security issue. Report it as a normal bug.

## Reporting

Use GitHub's private vulnerability reporting on the repository's Security tab. If that is not available, open an issue with a short description and say that you have details to share privately. Do not post a working exploit in a public issue before a fix is available.

Include:

- the version and the tool involved;
- the steps to reproduce;
- the operating system and Python version;
- what an attacker could do;
- any suggested fix.

## Response

This is a volunteer project. Reports are read as time allows. There is no guaranteed response time. A confirmed issue gets a fix in the next release and a note in `CHANGELOG.md` if it affects users.

## Scope

The scope covers the Python tools, the generated XML and Lua, and the Streets Unified companion in this repository. The Anno 1800 game itself and third-party mods are outside the scope.
