from pathlib import Path

import mobase
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMessageBox

from . import sweep


class OverwriteRegex(mobase.IPluginTool):
    def __init__(self) -> None:
        super().__init__()
        self._organizer: mobase.IOrganizer

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self._organizer = organizer
        organizer.onFinishedRun(self._onFinishedRun)
        return True

    def name(self) -> str:
        return "Overwrite Regex"

    def author(self) -> str:
        return "bsokol"

    def description(self) -> str:
        return "Moves files out of overwrite into mod folders, matched by regex."

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(0, 1, 0, mobase.ReleaseType.ALPHA)

    def settings(self) -> list[mobase.PluginSetting]:
        return [
            mobase.PluginSetting(
                "rules_file",
                "Path to the TOML rules file, relative to the MO2 base directory.",
                "overwrite_rules.toml",
            )
        ]

    def displayName(self) -> str:
        return "Overwrite Regex"

    def tooltip(self) -> str:
        return "Sort overwrite into mod folders by regex."

    def icon(self) -> QIcon:
        return QIcon()

    def display(self) -> None:
        counts = self._sweep()
        if counts is None:
            QMessageBox.warning(
                self._parentWidget(),
                "Overwrite Regex",
                f"No rules were applied. See mo_interface.log for details.\n\n"
                f"Rules file: {self._rulesPath()}",
            )
            return
        QMessageBox.information(
            self._parentWidget(),
            "Overwrite Regex",
            f"Moved {counts.moved} files.\n"
            f"{counts.skipped} skipped (mod folder missing).\n"
            f"{counts.unmatched} unmatched, left in overwrite.",
        )

    def _rulesPath(self) -> Path:
        setting = self._organizer.pluginSetting(self.name(), "rules_file")
        # A relative setting resolves against the MO2 base directory; pathlib
        # returns the right operand unchanged when it is already absolute.
        return Path(self._organizer.basePath()) / str(setting)

    def _sweep(self) -> sweep.Counts | None:
        rules = sweep.load_rules(self._rulesPath())
        if rules is None:
            return None
        return sweep.sweep(
            Path(self._organizer.overwritePath()), rules, self._resolveMod
        )

    def _resolveMod(self, name: str) -> Path | None:
        mod = self._organizer.modList().getMod(name)
        if mod is None:  # pyright: ignore[reportUnnecessaryComparison]
            return None
        return Path(mod.absolutePath())

    def _onFinishedRun(self, app_path: str, exit_code: int) -> None:
        self._sweep()
