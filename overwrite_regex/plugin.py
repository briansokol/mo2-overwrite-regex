import mobase
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMessageBox


class OverwriteRegex(mobase.IPluginTool):
    def __init__(self) -> None:
        super().__init__()
        self._organizer: mobase.IOrganizer

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self._organizer = organizer
        return True

    def name(self) -> str:
        return "Overwrite Regex"

    def author(self) -> str:
        return "bsokol"

    def description(self) -> str:
        return "Placeholder tool plugin."

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(0, 1, 0, mobase.ReleaseType.ALPHA)

    def settings(self) -> list[mobase.PluginSetting]:
        return []

    def displayName(self) -> str:
        return "Overwrite Regex"

    def tooltip(self) -> str:
        return "Placeholder tool plugin."

    def icon(self) -> QIcon:
        return QIcon()

    def display(self) -> None:
        QMessageBox.information(
            self._parentWidget(),
            "Overwrite Regex",
            f"Plugin loaded. Overwrite folder:\n{self._organizer.overwritePath()}",
        )
