# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Python plugin for Mod Organizer 2, targeting the local **MO2 2.5.2** install
at `/mnt/d/Modding Skyrim/MO2` (`D:\Modding Skyrim\MO2` in Windows).

## The runtime is not the venv

This is the most important thing to understand before changing dependencies.

`.venv` exists **only** so the editor and `pyright` can resolve types. At
runtime the plugin is executed by MO2's own embedded interpreter — Python 3.12
with PyQt6, at `MO2/plugins/plugin_python/libs/`. Nothing in `.venv` is on that
interpreter's path.

Consequences:

- **Adding a package with `uv add` does not make it importable at runtime.**
  The plugin may only import the standard library, `mobase`, and `PyQt6`. A
  third-party runtime dependency must be vendored into the plugin package
  directory instead.
- `mobase` is a stubs-only package (`mobase-stubs`). It has no source, so
  `reportMissingModuleSource` is disabled in `pyproject.toml`. Do not "fix"
  that warning by installing something.
- Keep `mobase-stubs` pinned to the MO2 version in use. It is currently
  `2.5.2`, matching the installed MO2 exactly. Upgrading MO2 means upgrading
  the stubs, or the types silently drift from reality.
- `requires-python` is `==3.12.*` to match the embedded interpreter. Do not
  widen it; language features newer than 3.12 will fail at runtime, not here.

## How MO2 loads the plugin

MO2 scans `MO2/plugins/` at startup, imports each package it finds, and calls
that package's `createPlugin()`. `overwrite_regex/__init__.py` defines that
function; it is the entry point and MO2 will not find the plugin without it.

`overwrite_regex/` is symlinked into `MO2/plugins/` (a Windows `mklink /D`,
see README), so edits in this repo are live in MO2 with no copy step.

**Failure mode to know:** if the import raises — a syntax error, a bad import,
an exception in `createPlugin()` — MO2 skips the plugin *silently*. It simply
does not appear in the Tools menu, with no error dialog. When a plugin goes
missing, read `MO2/logs/mo_interface.log` for the traceback rather than
guessing.

## Commands

```sh
uv sync                # set up .venv (Python 3.12 + dev tooling)
uv run ruff format .   # format
uv run ruff check .    # lint
uv run pyright         # type check — the meaningful check
```

There is **no test suite**, and no test framework is installed. `pyright` is
the substitute: because the plugin's whole surface is calls into a stubbed C++
API, a type error is almost always a real defect that would otherwise show up
as the silent load failure described above. Run it before every commit and
keep it at zero errors.

To exercise the plugin for real, reload it into a running MO2 rather than
restarting:

```sh
'/mnt/d/Modding Skyrim/MO2/ModOrganizer.exe' reload-plugin 'Overwrite Regex'
```

This is wired up as the default VS Code build task
(<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>B</kbd>). The plugin name passed to
`reload-plugin` must match the string returned by `name()` in `plugin.py`; if
you rename the plugin, update `.vscode/tasks.json` too.

## Workflow

- **Do all development on a feature branch.** Never commit directly to `main`.
  Branch first (`git checkout -b <type>/<short-description>`), then work.
- **Use Conventional Commits** for every commit message:
  `<type>(<optional scope>): <description>`, e.g. `feat(overwrite): match files
  by regex`, `fix: handle empty overwrite folder`, `chore(deps): bump
  mobase-stubs to 2.5.3`. Common types: `feat`, `fix`, `docs`, `refactor`,
  `test`, `chore`, `build`.
- **Never merge locally, and never push to `main`.** `main` is protected on
  GitHub: direct pushes are rejected and every change must arrive through a
  pull request. Push the feature branch and open a PR instead:

  ```sh
  git push -u origin <branch>
  gh pr create --fill
  ```

- **Squash or rebase when merging a PR**, never a merge commit. The branch
  requires linear history, so `gh pr merge --merge` is rejected; use
  `gh pr merge --squash --delete-branch` (or `--rebase`).
- Protection requires conversation resolution and forbids force pushes and
  branch deletion on `main`. Admins are exempt, so a bypass is possible in an
  emergency, but do not rely on it.
- Stage files by name. `.venv/` is gitignored but the directory is large and
  lives in the working tree.
- **Bump the version once per PR, before opening it.** Bump only when files
  under `overwrite_regex/` change; a PR touching only build scripts, docs, or
  config leaves the version alone. Pick the level from the change: `fix` is a
  patch, `feat` is a minor, and a breaking change to plugin behavior or
  settings is a minor while the version is `0.x` (a major once it reaches
  1.0). Update **both** `version` in `pyproject.toml` and
  `mobase.VersionInfo(...)` in `overwrite_regex/plugin.py`; they must never
  drift. Report it in the PR body as
  `Version: 0.1.0 -> 0.2.0 (minor: added regex preview)`, or
  `Version: unchanged (no plugin code changes)`.

## Environment quirks

This repo lives in a **OneDrive** folder on `/mnt/c`. Git and filesystem
operations here are slow — `git status`, `ls`, and recursive `find` can take
tens of seconds and have timed out at two minutes. Prefer targeted file checks
over recursive traversal, and give git commands a generous timeout rather than
assuming they hung.

If MO2 reports the plugin as missing or empty despite the symlink existing,
suspect OneDrive Files On-Demand has dehydrated the folder into placeholders.
