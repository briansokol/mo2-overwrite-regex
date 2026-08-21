# mo2-overwrite-regex

A Mod Organizer 2 plugin, written in Python.

Targets **MO2 2.5.2**, which embeds **Python 3.12** and **PyQt6**
(`MO2/plugins/plugin_python/libs/mobase.cp312-win_amd64.pyd`).

## Setup

Requires [uv](https://docs.astral.sh/uv/). From the repo root:

```sh
uv sync
```

This creates `.venv` on Python 3.12 with the development tools. Nothing here is
installed into MO2 — MO2 ships its own interpreter. These packages exist only so
the editor can autocomplete and type-check:

| Package        | Why                                              |
| -------------- | ------------------------------------------------ |
| `mobase-stubs` | Type stubs for the MO2 plugin API (`mobase`)      |
| `PyQt6`        | Qt typing, matching MO2's bundled Qt             |
| `ruff`         | Lint + format                                     |
| `pyright`      | Type checking from the CLI                        |

> If you edit from **Windows** VS Code rather than the WSL Remote extension,
> delete `.venv` and rerun `uv sync` from PowerShell so the venv is a Windows
> one. Also update `python.defaultInterpreterPath` in `.vscode/settings.json`
> to `.venv/Scripts/python.exe`.

## Installing the plugin into MO2

MO2 loads plugins from `MO2/plugins/`. Symlink this repo's package folder there
so edits are live with no copy step. Run once in an **Administrator** Command
Prompt (or enable Windows Developer Mode to skip the admin requirement):

```cmd
mklink /D "D:\Modding Skyrim\MO2\plugins\overwrite_regex" "C:\Users\bsoko\OneDrive\Documents\Visual Studio Projects\mo2-overwrite-regex\overwrite_regex"
```

Verify: launch MO2 and look for **Overwrite Regex** in the Tools menu (the
puzzle-piece icon). It opens the rules editor.

## Configuration

Settings > Plugins > Overwrite Regex has one setting:

| Setting      | Default                | Meaning                                              |
| ------------ | ---------------------- | ---------------------------------------------------- |
| `rules_file` | `overwrite_rules.toml` | Rules file path, relative to the MO2 base directory. An absolute path is used as-is. |

Tools > Overwrite Regex creates that file, empty, if it does not exist. It
sits next to `ModOrganizer.ini`:

```toml
# overwrite_rules.toml
# First match wins, top to bottom.

[[rule]]
pattern = '^logs/.*\.log$'
mod = "My Logs Mod"

[[rule]]
pattern = '\.dds$'
mod = "Generated Textures"
```

Each `pattern` is a Python regex, matched with `re.search` and case
insensitively, against the file's path relative to `overwrite`, using forward
slashes: `logs/papyrus.0.log`. Anchor with `^` or `$` where it matters.

Editing by hand, use TOML **literal strings** (single quotes) for patterns.
They perform no escape processing, so `'\.dds$'` is the regex you typed. Double
quotes would require `"\\.dds$"`. The rules editor writes double-quoted strings
and escapes them for you, and rewrites the whole file, so comments and hand
formatting are lost the first time you save from it.

`mod` is the mod's folder name under `MO2/mods/`.

A missing rules file, malformed TOML, or a rule whose `pattern` or `mod` is
not a string aborts the entire sweep: nothing moves. A single pattern that
fails to compile as a regex only drops that one rule; the remaining rules
still apply. Both cases log to `MO2/logs/mo_interface.log`.

The sweep runs after MO2 finishes running any application it launched, not
just the game: xEdit, LOOT, and similar tools trigger it too, since MO2 tears
down its virtual filesystem after each one. Each file in `overwrite` moves to
the first matching mod, keeping its nested path. If the mod already has a
file at that path, it is silently overwritten. Unmatched files stay put. A
rule naming a mod that is not installed logs a warning to
`MO2/logs/mo_interface.log` and leaves the file alone. Every empty directory
left under `overwrite` afterward is deleted, including ones that were already
empty before the sweep, even if no file moved.

## The rules editor

Tools > Overwrite Regex opens the rules in a table instead of sweeping. Add and
remove rows, then close the window to write them back to the rules file.

A pattern that will not compile, or an empty pattern or mod, turns its cell red
and shows the reason as a tooltip. Such rows are still saved, so a half-finished
rule survives a close, but they are left out of any sweep.

**Dry Run** matches the rules currently in the table against the files now in
`overwrite` and lists where each one would go, without moving anything. It
checks matching only: a mod that is not installed still shows as a destination.

**Run Sweep** performs the sweep with the rules currently in the table, saved or
not.

The file is re-read on every sweep, so edits apply without restarting MO2.

## Development loop

Edit, then reload the plugin without restarting MO2:

```sh
'/mnt/d/Modding Skyrim/MO2/ModOrganizer.exe' reload-plugin 'Overwrite Regex'
```

This is wired up as the default VS Code build task, so <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>B</kbd>
reloads. To reload automatically on every save, install the
[Trigger Task on Save](https://marketplace.visualstudio.com/items?itemName=Gruntfuggly.triggertaskonsave)
extension and point it at the `Reload MO2 plugin` task.

On Windows, the same command is:

```cmd
"D:\Modding Skyrim\MO2\ModOrganizer.exe" reload-plugin "Overwrite Regex"
```

## Checks

```sh
uv run ruff format .   # format
uv run ruff check .    # lint
uv run pyright         # type check
```

`pyright` is the meaningful one: it is what catches a misused `mobase` API
before MO2 silently refuses to load the plugin.

## Layout

```
overwrite_regex/       # the plugin package — this is what gets symlinked
├── __init__.py        # createPlugin(), MO2's required entry point
├── plugin.py          # the IPluginTool implementation and MO2 glue
├── dialog.py          # the rules editor dialog
└── sweep.py           # rules file I/O, matching, and moving; no mobase
```

MO2 discovers a Python plugin by importing the package and calling
`createPlugin()`. If that function is missing or raises, the plugin is skipped —
check `MO2/logs/` when a plugin fails to appear.

## Troubleshooting

**Plugin doesn't appear in MO2.** Check `MO2/logs/mo_interface.log` for an import
traceback. A syntax error or bad import makes MO2 skip the plugin silently.

**Files look empty or missing to MO2.** This repo lives in OneDrive. If Files
On-Demand has dehydrated the folder, MO2 may see placeholders. Right-click the
repo folder in Explorer and choose *Always keep on this device*.
