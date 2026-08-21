"""Rules editor for the Overwrite Regex plugin.

Edits are held in the table and written to the TOML file when the dialog
closes. Both Dry Run and Run Sweep use the table as it stands, so a rule can
be tried before it is saved.
"""

import re
from collections.abc import Callable
from pathlib import Path

from PyQt6.QtGui import QBrush, QColor, QFontDatabase
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import sweep

_INVALID = QColor(255, 160, 160)


def _pattern_error(pattern: str) -> str | None:
    if not pattern:
        return "Pattern is empty."
    try:
        re.compile(pattern)
    except re.error as error:
        return str(error)
    return None


class RulesDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        path: Path,
        rows: list[sweep.Row],
        overwrite: Path,
        run_sweep: Callable[[list[sweep.Rule]], sweep.Counts],
    ) -> None:
        super().__init__(parent)
        self._path = path
        self._overwrite = overwrite
        self._run_sweep = run_sweep

        self.setWindowTitle("Overwrite Regex")
        self.resize(760, 560)

        self._table = QTableWidget(0, 2, self)
        self._table.setHorizontalHeaderLabels(["Pattern", "Mod"])
        # Never None in practice; the stubs say otherwise.
        if (header := self._table.horizontalHeader()) is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        for pattern, mod in rows:
            self._appendRow(pattern, mod)
        self._table.itemChanged.connect(self._validate)

        self._report = QPlainTextEdit(self)
        self._report.setReadOnly(True)
        self._report.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self._report.setPlaceholderText(
            "Dry Run reports where each file now in overwrite would go."
        )

        add = QPushButton("Add rule", self)
        add.clicked.connect(lambda: self._appendRow())
        remove = QPushButton("Remove selected", self)
        remove.clicked.connect(self._removeRows)
        dry_run = QPushButton("Dry Run", self)
        dry_run.clicked.connect(self._dryRun)
        run = QPushButton("Run Sweep", self)
        run.clicked.connect(self._onRunSweep)
        close = QPushButton("Close", self)
        close.clicked.connect(self.close)

        edit_buttons = QHBoxLayout()
        edit_buttons.addWidget(add)
        edit_buttons.addWidget(remove)
        edit_buttons.addStretch()

        bottom_buttons = QHBoxLayout()
        bottom_buttons.addWidget(dry_run)
        bottom_buttons.addWidget(run)
        bottom_buttons.addStretch()
        bottom_buttons.addWidget(close)

        layout = QVBoxLayout(self)
        layout.addWidget(self._table)
        layout.addLayout(edit_buttons)
        layout.addWidget(self._report)
        layout.addLayout(bottom_buttons)

    def done(self, a0: int) -> None:
        """Save on the way out, whichever way the dialog was dismissed."""
        try:
            sweep.save_rules(self._path, self._rows())
        except OSError as error:
            QMessageBox.warning(
                self, "Overwrite Regex", f"Cannot write {self._path}:\n{error}"
            )
        super().done(a0)

    def _appendRow(self, pattern: str = "", mod: str = "") -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        for column, text in enumerate((pattern, mod)):
            item = QTableWidgetItem(text)
            self._table.setItem(row, column, item)
            self._validate(item)

    def _removeRows(self) -> None:
        for row in sorted(
            {index.row() for index in self._table.selectedIndexes()}, reverse=True
        ):
            self._table.removeRow(row)

    def _validate(self, item: QTableWidgetItem) -> None:
        if item.column() == 0:
            error = _pattern_error(item.text())
        else:
            error = None if item.text() else "Mod name is empty."
        # Marking the item is itself a change; without this the handler would
        # re-enter on its own edit.
        self._table.blockSignals(True)
        item.setToolTip(error or "")
        item.setBackground(QBrush(_INVALID) if error else QBrush())
        self._table.blockSignals(False)

    def _rows(self) -> list[sweep.Row]:
        def text(row: int, column: int) -> str:
            item = self._table.item(row, column)
            return item.text() if item is not None else ""

        return [(text(row, 0), text(row, 1)) for row in range(self._table.rowCount())]

    def _rules(self) -> list[sweep.Rule]:
        """Compile the table, leaving the rows flagged as invalid out of it."""
        return sweep.compile_rules(
            [(pattern, mod) for pattern, mod in self._rows() if pattern and mod]
        )

    def _dryRun(self) -> None:
        entries = sweep.plan(self._overwrite, self._rules())
        matched = sum(1 for _, mod in entries if mod is not None)
        width = max((len(relative) for relative, _ in entries), default=0)
        self._report.setPlainText(
            "\n".join(
                [
                    (
                        f"{len(entries)} files in overwrite, {matched} matched, "
                        f"{len(entries) - matched} unmatched."
                    ),
                    "",
                    *(
                        f"{relative:<{width}}  ->  {mod or '(no match)'}"
                        for relative, mod in entries
                    ),
                ]
            )
        )

    def _onRunSweep(self) -> None:
        counts = self._run_sweep(self._rules())
        self._report.setPlainText(
            f"Moved {counts.moved} files.\n"
            f"{counts.skipped} skipped (see mo_interface.log).\n"
            f"{counts.unmatched} unmatched, left in overwrite."
        )
