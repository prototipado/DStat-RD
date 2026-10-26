"""Theme management: load QSS, persist preference, apply to QApplication."""

from __future__ import annotations

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

from .theme import LIGHT, DARK, palette_for, render_qss

SETTINGS_ORG = "Wheeler Microfluidics Laboratory"
SETTINGS_APP = "DStat GUI"
THEME_KEY = "ui/theme"


def load_preference() -> str:
    """Return persisted theme mode: 'system', 'light' or 'dark'."""
    settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
    value = settings.value(THEME_KEY, "system")
    if value not in ("system", "light", "dark"):
        return "system"
    return value


def save_preference(mode: str) -> None:
    settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
    settings.setValue(THEME_KEY, mode)
    settings.sync()


def current_mode() -> str:
    return load_preference()


def apply_theme(app: QApplication, mode: str | None = None) -> str:
    """Apply the requested (or persisted) theme. Returns the resolved mode."""
    if mode is None:
        mode = load_preference()
    if mode not in ("system", "light", "dark"):
        mode = "system"
    palette = palette_for(mode)
    qss = render_qss(palette)
    app.setStyleSheet(qss)
    # Keep a reference for other modules (matplotlib, etc.)
    app.setProperty("dstat_theme_mode", mode)
    app.setProperty("dstat_palette", palette)
    return mode


def resolved_palette(app: QApplication | None = None):
    if app is None:
        app = QApplication.instance()
    if app is not None:
        p = app.property("dstat_palette")
        if p is not None:
            return p
    return palette_for(load_preference())
