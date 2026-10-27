"""Matplotlib plot widget embedded in Qt.

Each experiment can own multiple `PlotWidget` instances (one per axes set).
The widget creates real matplotlib figures and exposes helpers to update
lines in real time as experiment data arrive.
"""

import logging
import os

import numpy as np
import matplotlib
matplotlib.use("QtAgg")

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as _NavToolbar,
)
from PyQt6.QtGui import QIcon
import matplotlib.gridspec as gridspec

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

from .theme import ACCENT, FONT_FAMILY
from .theme_manager import resolved_palette

logger = logging.getLogger(__name__)

_ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")


class ThemedNavigationToolbar(_NavToolbar):
    """NavigationToolbar using our SVG icons, themed light/dark."""

    def __init__(self, canvas, parent=None, coordinates=True):
        self._dark = False
        super().__init__(canvas, parent, coordinates=coordinates)
        self._refresh_icons()

    def set_dark(self, dark: bool):
        self._dark = dark
        self._refresh_icons()

    def _refresh_icons(self):
        suffix = "dark" if self._dark else "light"
        for action in self.actions():
            tip = action.toolTip() or action.text() or ""
            # map by tooltip keywords
            pass
        # Rebuild icons by matching toolitem image names is not trivial after build;
        # instead reload each action's icon from our svg based on its text.
        name_map = {
            "Home": "home", "Back": "back", "Forward": "forward",
            "Pan": "move", "Zoom": "zoom_to_rect",
            "Subplots": "subplots", "Customize": "qt4_editor_options",
            "Save": "filesave",
        }
        for action in self.actions():
            key = name_map.get(action.text())
            if key:
                path = os.path.join(_ICONS_DIR, "%s_%s.svg" % (key, suffix))
                if os.path.exists(path):
                    action.setIcon(QIcon(path))


class PlotWidget(QWidget):
    """A QWidget that contains a matplotlib Figure with a navigation toolbar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = ThemedNavigationToolbar(self.canvas, self)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        self.subplots: dict = {}
        self._lines: dict = {}

        self.apply_theme()

    def apply_theme(self, palette=None):
        """Restyle the figure and all axes according to the active theme."""
        if palette is None:
            palette = resolved_palette()
        dark = (palette.name == "dark")
        bg = palette.bg
        card = palette.card
        fg = palette.fg
        muted = palette.fg_muted
        grid = palette.border

        self.figure.set_facecolor(card)
        self.canvas.setStyleSheet("background-color: %s;" % card)
        self.toolbar.set_dark(dark)

        for ax in self.figure.axes:
            ax.set_facecolor(bg if dark else card)
            ax.tick_params(colors=fg, labelsize=9)
            ax.xaxis.label.set_color(fg)
            ax.yaxis.label.set_color(fg)
            ax.title.set_color(fg)
            for spine in ax.spines.values():
                spine.set_color(grid)
            ax.grid(True, color=grid, alpha=0.35, linestyle="--", linewidth=0.8)
            for line in ax.get_lines():
                if line.get_color() in ("C0", "#1f77b4"):
                    line.set_color(ACCENT)
                    line.set_linewidth(1.8)

        self.canvas.draw_idle()

    def setup_axes(self, plot_format: dict):
        """Create subplots from a plot_format dict (key → {xlabel, ylabel})."""
        self.figure.clf()
        n = len(plot_format)
        gs = gridspec.GridSpec(n, 1, figure=self.figure)
        self.subplots = {}
        self._lines = {}

        palette = resolved_palette()
        dark = (palette.name == "dark")
        bg = palette.bg
        card = palette.card
        fg = palette.fg
        grid = palette.border

        self.figure.set_facecolor(card)

        for idx, (key, fmt) in enumerate(plot_format.items()):
            ax = self.figure.add_subplot(gs[idx])
            ax.set_facecolor(bg if dark else card)
            ax.ticklabel_format(style="sci", scilimits=(0, 3), useOffset=False, axis="y")
            ax.set_xlabel(fmt.get("xlabel", ""))
            ax.set_ylabel(fmt.get("ylabel", ""))
            ax.tick_params(colors=fg, labelsize=9)
            ax.xaxis.label.set_color(fg)
            ax.yaxis.label.set_color(fg)
            for spine in ax.spines.values():
                spine.set_color(grid)
            ax.grid(True, color=grid, alpha=0.35, linestyle="--", linewidth=0.8)
            (line,) = ax.plot([], [], color=ACCENT, linewidth=1.8)
            self.subplots[key] = ax
            self._lines[key] = [line]

        self.canvas.draw_idle()

    def update_data(self, key: str, x_data, y_data, scan: int = 0):
        """Update (or add) a line for the given scan index."""
        ax = self.subplots.get(key)
        if ax is None:
            return

        # Grow lines list as new scans arrive
        while scan >= len(self._lines[key]):
            (new_line,) = ax.plot([], [])
            self._lines[key].append(new_line)

        line = self._lines[key][scan]
        line.set_xdata(x_data)
        line.set_ydata(y_data)
        ax.relim()
        ax.autoscale_view()
        self.canvas.draw_idle()

    def save_plot(self, path: str):
        self.figure.savefig(path)
