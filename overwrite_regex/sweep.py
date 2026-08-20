"""Core of the Overwrite Regex plugin.

Deliberately free of ``mobase`` so it can be imported and self-checked inside
``.venv``, where ``mobase`` is stubs-only. All MO2 glue lives in ``plugin.py``.
"""

import re
import shutil
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from PyQt6.QtCore import qWarning

Rule = tuple[re.Pattern[str], str]


class Counts(NamedTuple):
    moved: int
    skipped: int
    unmatched: int


def load_rules(path: Path) -> list[Rule] | None:
    """Parse the TOML rules file.

    ``None`` means do not sweep at all. A half-applied broken rules file is
    worse than none, so any structural problem aborts. A single pattern that
    will not compile is isolated: that rule is dropped, the rest still apply.
    """
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError:
        qWarning(f"Overwrite Regex: no rules file at {path}")
        return None
    except (OSError, tomllib.TOMLDecodeError) as error:
        qWarning(f"Overwrite Regex: cannot read {path}: {error}")
        return None

    entries = data.get("rule", [])
    if not isinstance(entries, list):
        qWarning(f"Overwrite Regex: 'rule' in {path} must be a list of [[rule]] tables")
        return None

    rules: list[Rule] = []
    for index, entry in enumerate(entries):
        pattern = entry.get("pattern") if isinstance(entry, dict) else None
        mod = entry.get("mod") if isinstance(entry, dict) else None
        if not isinstance(pattern, str) or not isinstance(mod, str):
            qWarning(
                f"Overwrite Regex: rule {index} in {path} needs a string "
                f"'pattern' and a string 'mod'"
            )
            return None
        try:
            rules.append((re.compile(pattern, re.IGNORECASE), mod))
        except re.error as error:
            qWarning(f"Overwrite Regex: skipping invalid pattern {pattern!r}: {error}")

    return rules


def sweep(
    overwrite: Path,
    rules: list[Rule],
    resolve_mod: Callable[[str], Path | None],
) -> Counts:
    """Route every file under ``overwrite`` by the first rule that matches it."""
    moved = skipped = unmatched = 0

    # sorted() drains the generator before any file moves, so the walk is not
    # invalidated by the moves it triggers.
    for source in sorted(overwrite.rglob("*")):
        if not source.is_file():
            continue

        relative = source.relative_to(overwrite).as_posix()
        mod = next((name for pattern, name in rules if pattern.search(relative)), None)
        if mod is None:
            unmatched += 1
            continue

        root = resolve_mod(mod)
        if root is None:
            qWarning(
                f"Overwrite Regex: mod {mod!r} is not installed, "
                f"leaving {relative} in overwrite"
            )
            skipped += 1
            continue

        destination = root / relative
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(source, destination)
        except OSError as error:
            qWarning(f"Overwrite Regex: cannot move {relative}: {error}")
            skipped += 1
            continue

        moved += 1

    _prune_empty_dirs(overwrite)
    return Counts(moved, skipped, unmatched)


def _prune_empty_dirs(root: Path) -> None:
    """Remove empty directories under ``root``, deepest first. ``root`` stays.

    MO2 shows overwrite as non-empty when it holds only empty directories, so
    skipping this makes a fully successful sweep look like it did nothing.
    """
    # Reverse lexical order is deepest first, because a child's path string
    # always begins with its parent's.
    for directory in sorted((p for p in root.rglob("*") if p.is_dir()), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass  # Still holds something. Normal, and not worth a warning.


def _check_load_rules() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        good = base / "good.toml"
        good.write_text(
            "[[rule]]\n"
            "pattern = '^logs/'\n"
            'mod = "Logs"\n'
            "\n"
            "[[rule]]\n"
            "pattern = '\\.dds$'\n"
            'mod = "Textures"\n'
        )
        rules = load_rules(good)
        assert rules is not None, "a valid file must not abort the sweep"
        assert [m for _, m in rules] == ["Logs", "Textures"], "order must be preserved"
        assert rules[0][0].search("LOGS/x.txt"), "patterns must be case insensitive"
        assert rules[1][0].search("a/b.dds"), "literal strings must not need escaping"

        empty = base / "empty.toml"
        empty.write_text("")
        assert load_rules(empty) == [], "no rules is not the same as no file"

        assert load_rules(base / "absent.toml") is None, "missing file aborts"

        malformed = base / "malformed.toml"
        malformed.write_text("[[rule]]\npattern = \n")
        assert load_rules(malformed) is None, "bad TOML aborts"

        wrong_type = base / "wrong_type.toml"
        wrong_type.write_text("[[rule]]\npattern = 1\nmod = 2\n")
        assert load_rules(wrong_type) is None, "non-string pattern or mod aborts"

        missing_key = base / "missing_key.toml"
        missing_key.write_text("[[rule]]\npattern = '^logs/'\n")
        assert load_rules(missing_key) is None, "a rule without 'mod' aborts"

        not_a_list = base / "not_a_list.toml"
        not_a_list.write_text('rule = "oops"\n')
        assert load_rules(not_a_list) is None, "'rule' must be an array of tables"

        bad_regex = base / "bad_regex.toml"
        bad_regex.write_text(
            "[[rule]]\n"
            "pattern = '('\n"
            'mod = "Broken"\n'
            "\n"
            "[[rule]]\n"
            "pattern = 'ok'\n"
            'mod = "Fine"\n'
        )
        survivors = load_rules(bad_regex)
        assert survivors is not None, "one bad pattern must not abort the file"
        assert [m for _, m in survivors] == ["Fine"], "only the bad rule is dropped"

    print("load_rules self-check OK")


def _check_sweep() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        overwrite = base / "overwrite"
        mods = base / "mods"

        rules_file = base / "rules.toml"
        rules_file.write_text(
            "[[rule]]\n"
            "pattern = '^logs/'\n"
            'mod = "Logs"\n'
            "\n"
            "[[rule]]\n"
            "pattern = '\\.log$'\n"
            'mod = "Never"\n'
            "\n"
            "[[rule]]\n"
            "pattern = '\\.dds$'\n"
            'mod = "Textures"\n'
            "\n"
            "[[rule]]\n"
            "pattern = '^gone/'\n"
            'mod = "NotInstalled"\n'
        )
        rules = load_rules(rules_file)
        assert rules is not None

        for relative, body in [
            ("logs/papyrus.0.log", "a"),
            ("logs/nested/deep.log", "b"),
            ("textures/gen/x.dds", "c"),
            ("gone/orphan.txt", "d"),
            ("readme.txt", "e"),
            ("notes/todo.txt", "f"),
        ]:
            path = overwrite / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
        (overwrite / "already-empty").mkdir()

        # "Never" is installed on purpose: if rule order broke, the first file
        # would land there instead of in Logs, and the counts would not notice.
        for name in ("Logs", "Never", "Textures"):
            (mods / name).mkdir(parents=True)
        stale = mods / "Logs" / "logs" / "papyrus.0.log"
        stale.parent.mkdir(parents=True)
        stale.write_text("stale")

        def resolve(name: str) -> Path | None:
            candidate = mods / name
            return candidate if candidate.is_dir() else None

        counts = sweep(overwrite, rules, resolve)

        assert counts == Counts(moved=3, skipped=1, unmatched=2), counts
        assert stale.read_text() == "a", "an existing destination file is overwritten"
        assert not (mods / "Never" / "logs").exists(), "first matching rule wins"
        assert (mods / "Logs" / "logs" / "nested" / "deep.log").read_text() == "b", (
            "nested structure is reproduced under the mod"
        )
        assert (mods / "Textures" / "textures" / "gen" / "x.dds").read_text() == "c"
        assert (overwrite / "gone" / "orphan.txt").read_text() == "d", (
            "an uninstalled mod leaves the file in overwrite"
        )
        assert (overwrite / "readme.txt").read_text() == "e", "unmatched files stay"
        assert (overwrite / "notes" / "todo.txt").read_text() == "f", (
            "a nested unmatched file stays where it is"
        )
        assert not (overwrite / "logs").exists(), "emptied directories are pruned"
        assert not (overwrite / "already-empty").exists(), "already-empty are pruned"
        assert (overwrite / "gone").is_dir(), "directories with files are kept"
        assert overwrite.is_dir(), "the overwrite root is never removed"

    print("sweep self-check OK")


if __name__ == "__main__":
    _check_load_rules()
    _check_sweep()
