from pathlib import Path

import mobase
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMessageBox

from . import sweep
from .dialog import RulesDialog


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
        path = self._rulesPath()
        if not path.exists():
            try:
                sweep.save_rules(path, [])
            except OSError as error:
                QMessageBox.warning(
                    self._parentWidget(),
                    "Overwrite Regex",
                    f"Cannot create {path}:\n{error}",
                )
                return

        rows = sweep.load_rules(path)
        if rows is None:
            # Opening on an empty table would overwrite a file that is broken
            # but still holds the user's rules.
            QMessageBox.warning(
                self._parentWidget(),
                "Overwrite Regex",
                f"{path} could not be read. See mo_interface.log for details.\n\n"
                f"Fix or delete the file, then open this again.",
            )
            return

        RulesDialog(
            self._parentWidget(),
            path,
            rows,
            Path(self._organizer.overwritePath()),
            self._runSweep,
        ).exec()

    def _rulesPath(self) -> Path:
        setting = self._organizer.pluginSetting(self.name(), "rules_file")
        # A relative setting resolves against the MO2 base directory; pathlib
        # returns the right operand unchanged when it is already absolute.
        return Path(self._organizer.basePath()) / str(setting)

    def _sweep(self) -> sweep.Counts | None:
        rows = sweep.load_rules(self._rulesPath())
        if rows is None:
            return None
        return sweep.sweep(
            Path(self._organizer.overwritePath()),
            sweep.compile_rules(rows),
            self._resolveMod,
        )

    def _runSweep(self, rules: list[sweep.Rule]) -> sweep.Counts:
        """Sweep on the dialog's behalf, with the rules it has on screen."""
        counts = sweep.sweep(
            Path(self._organizer.overwritePath()), rules, self._resolveMod
        )
        if counts.moved:
            # Only on this path. MO2 refreshes on its own once an application
            # exits, so _onFinishedRun would be asking for a second one.
            self._organizer.refresh()
        return counts

    def _resolveMod(self, name: str) -> Path | None:
        mod = self._organizer.modList().getMod(name)
        if mod is None:
            return None
        return Path(mod.absolutePath())

    def _onFinishedRun(self, app_path: str, exit_code: int) -> None:
        self._sweep()
