"""Protocol terminal widget.

Shows the serial conversation between the GUI and the DStat as it happens:
every command written to the instrument and every line it answers.  This is
meant for reviewing the protocol, so the entries are colour-coded by direction
and unexpected replies are highlighted.

The transport side lives in :mod:`dstat_interface.core.dstat.comm`; this module
only renders ``(kind, text)`` tuples collected by ``SerialConnection.get_trace``.
"""

import logging
import re
import time

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit, QCheckBox,
    QPushButton, QFileDialog, QSizePolicy,
)
from PyQt6.QtGui import QFontDatabase, QTextCharFormat, QTextCursor, QColor
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)

# Entry kinds produced by comm.SerialTrace.
KIND_SYMBOLS = {
    "tx": "\u2192",     # -> GUI to DStat
    "rx": "\u2190",     # <- DStat to GUI
    "info": "\u00b7",   # firmware commentary / progress notes
    "warn": "!",
    "error": "\u00d7",
}

KIND_COLORS = {
    "tx": "#1565c0",     # blue
    "rx": "#1b5e20",     # green
    "info": "#6b6b6b",   # grey
    "warn": "#a35200",   # amber
    "error": "#c62828",  # red
}

KIND_TOOLTIPS = {
    "tx": "Sent by the GUI to the DStat",
    "rx": "Received from the DStat",
    "info": "Firmware information / progress",
    "warn": "Unexpected reply (the command was retried)",
    "error": "Command that could not be delivered",
}

_TRAILING_SPACES = re.compile(r"( +)$")


def visible_text(text: str) -> str:
    """Make protocol-significant whitespace visible.

    Commands are length-prefixed by ``strlen()`` and often end with a space
    that the firmware counts, so trailing spaces are rendered as middle dots.
    """
    text = text.replace("\r", "\\r").replace("\t", "\\t")
    match = _TRAILING_SPACES.search(text)
    if match:
        text = text[:match.start()] + "\u00b7" * len(match.group(1))
    return text


class ProtocolView(QWidget):
    """Read-only, colour-coded view of the DStat serial protocol."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel("Protocol")
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch()

        hint = QLabel("GUI \u2192 DStat / DStat \u2192 GUI")
        hint.setStyleSheet("color: #777;")
        hint.setWordWrap(True)
        header.addWidget(hint)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setToolTip("Clear the protocol log")
        self.btn_clear.clicked.connect(self.clear)
        header.addWidget(self.btn_clear)

        self.btn_save = QPushButton("Save\u2026")
        self.btn_save.setToolTip("Write the current log to a text file")
        self.btn_save.clicked.connect(self.save_log)
        header.addWidget(self.btn_save)
        layout.addLayout(header)

        filters = QVBoxLayout()
        filters.setSpacing(4)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.check_tx = QCheckBox("GUI \u2192 DStat")
        self.check_tx.setChecked(True)
        self.check_tx.setStyleSheet("color: {};".format(KIND_COLORS["tx"]))
        row1.addWidget(self.check_tx)

        self.check_rx = QCheckBox("DStat \u2192 GUI")
        self.check_rx.setChecked(True)
        self.check_rx.setStyleSheet("color: {};".format(KIND_COLORS["rx"]))
        row1.addWidget(self.check_rx)
        row1.addStretch()
        filters.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.check_notes = QCheckBox("Notas")
        self.check_notes.setChecked(True)
        self.check_notes.setToolTip("Firmware information, warnings and errors")
        row2.addWidget(self.check_notes)

        self.check_autoscroll = QCheckBox("Auto-scroll")
        self.check_autoscroll.setChecked(True)
        row2.addWidget(self.check_autoscroll)
        row2.addStretch()
        filters.addLayout(row2)

        layout.addLayout(filters)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.text.setMaximumBlockCount(5000)
        self.text.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.text.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.text.setPlaceholderText(
            "El tráfico serial aparecerá acá al conectar el DStat."
        )
        layout.addWidget(self.text, 1)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def is_kind_visible(self, kind: str) -> bool:
        if kind == "tx":
            return self.check_tx.isChecked()
        if kind == "rx":
            return self.check_rx.isChecked()
        return self.check_notes.isChecked()

    def append(self, kind: str, text: str, timestamp=None):
        """Append one protocol entry, colour-coded by *kind*."""
        if not self.is_kind_visible(kind):
            return

        stamp = time.strftime("%H:%M:%S", time.localtime(timestamp))
        if timestamp is not None:
            millis = int((timestamp % 1) * 1000)
            stamp = "{}.{:03d}".format(stamp, millis)

        cursor = QTextCursor(self.text.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if not self.text.document().isEmpty():
            cursor.insertBlock()

        time_format = QTextCharFormat()
        time_format.setForeground(QColor("#9e9e9e"))
        cursor.insertText(stamp + " ", time_format)

        colour = KIND_COLORS.get(kind, KIND_COLORS["info"])
        entry_format = QTextCharFormat()
        entry_format.setForeground(QColor(colour))
        if kind == "error":
            entry_format.setFontWeight(700)

        symbol = KIND_SYMBOLS.get(kind, "\u00b7")
        cursor.insertText("{} ".format(symbol), entry_format)
        cursor.insertText(visible_text(text), entry_format)

        if self.check_autoscroll.isChecked():
            self.text.setTextCursor(cursor)
            self.text.ensureCursorVisible()

    def append_entries(self, entries):
        """Append an iterable of ``(kind, text)`` tuples with one shared time."""
        now = time.time()
        for kind, text in entries:
            self.append(kind, text, timestamp=now)

    def clear(self):
        self.text.clear()

    def save_log(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save protocol log",
            "dstat-protocol.log",
            "Log files (*.log *.txt);;All files (*)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self.text.toPlainText())
        except OSError as exc:
            logger.error("Could not save protocol log: %s", exc)
        else:
            logger.info("Protocol log saved to %s", path)

    def plain_text(self) -> str:
        """Return the log contents (used by tests)."""
        return self.text.toPlainText()
