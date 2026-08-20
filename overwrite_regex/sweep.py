"""Core of the Overwrite Regex plugin.

Deliberately free of ``mobase`` so it can be imported and self-checked inside
``.venv``, where ``mobase`` is stubs-only. All MO2 glue lives in ``plugin.py``.
"""

import re
import tomllib
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


if __name__ == "__main__":
    _check_load_rules()
