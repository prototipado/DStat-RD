"""Raw data and info display widgets."""

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QTextEdit, QTableWidget,
    QTableWidgetItem, QLabel,
)
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


class DataView(QWidget):
    """Displays raw numeric data from the last experiment in a table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def populate(self, columns: list, rows: list):
        """Fill table with *columns* header list and *rows* list-of-lists."""
        self.table.clear()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                item = QTableWidgetItem(f"{val:.6g}" if isinstance(val, float) else str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()

    def clear(self):
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)


class InfoView(QWidget):
    """Displays log messages and DStat hardware info."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)

    def append(self, message: str):
        self.text.append(message)

    def clear(self):
        self.text.clear()
