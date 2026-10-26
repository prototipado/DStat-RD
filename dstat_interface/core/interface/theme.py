"""Design tokens and theme helpers for DStat GUI 2.1.

All colour/typography/spacing values live here so the rest of the codebase
never hard-codes a colour.  The QSS template is stored in ``styles.qss`` and
rendered with :func:`render_qss` using the active palette.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Accent (single source of truth)
# ---------------------------------------------------------------------------
ACCENT = "#0d9488"
ACCENT_HOVER = "#0f766e"
ACCENT_PRESSED = "#115e59"
ACCENT_LIGHT = "#5eead4"

DANGER = "#dc2626"
DANGER_HOVER = "#b91c1c"
SUCCESS = "#16a34a"
WARNING = "#d97706"

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------
FONT_FAMILY = "Segoe UI, Inter, 'Helvetica Neue', Arial, sans-serif"
FONT_MONO = "Consolas, 'Cascadia Mono', 'JetBrains Mono', monospace"
FONT_SIZE_BASE = 10  # pt
FONT_SIZE_SMALL = 9
FONT_SIZE_TITLE = 13
FONT_SIZE_HEADING = 11

# ---------------------------------------------------------------------------
# Spacing / geometry
# ---------------------------------------------------------------------------
RADIUS = 8
RADIUS_SMALL = 6
SPACING = 8
MARGIN = 10


@dataclass
class Palette:
    name: str
    bg: str
    bg_alt: str
    card: str
    border: str
    fg: str
    fg_muted: str
    fg_disabled: str
    input_bg: str
    input_border: str
    input_focus: str
    hover: str
    selected: str
    scrollbar: str
    shadow: str


LIGHT = Palette(
    name="light",
    bg="#f5f7fa",
    bg_alt="#eef1f5",
    card="#ffffff",
    border="#d9dee5",
    fg="#1f2937",
    fg_muted="#6b7280",
    fg_disabled="#9ca3af",
    input_bg="#ffffff",
    input_border="#c7ccd4",
    input_focus=ACCENT,
    hover="#f0fdfa",
    selected="#ccfbf1",
    scrollbar="#c7ccd4",
    shadow="rgba(0,0,0,0.06)",
)

DARK = Palette(
    name="dark",
    bg="#111827",
    bg_alt="#1f2937",
    card="#1f2937",
    border="#374151",
    fg="#e5e7eb",
    fg_muted="#9ca3af",
    fg_disabled="#6b7280",
    input_bg="#111827",
    input_border="#4b5563",
    input_focus=ACCENT,
    hover="#134e4a",
    selected="#134e4a",
    scrollbar="#4b5563",
    shadow="rgba(0,0,0,0.35)",
)


def system_prefers_dark() -> bool:
    """Best-effort detection of the OS colour scheme (Windows 10/11)."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return value == 0
    except Exception:
        return False


def palette_for(mode: str) -> Palette:
    mode = (mode or "").lower()
    if mode == "dark":
        return DARK
    if mode == "light":
        return LIGHT
    # system
    return DARK if system_prefers_dark() else LIGHT


def qss_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles.qss")


def render_qss(palette: Palette) -> str:
    with open(qss_path(), encoding="utf-8") as f:
        template = f.read()
    tokens = {
        "bg": palette.bg,
        "bg_alt": palette.bg_alt,
        "card": palette.card,
        "border": palette.border,
        "fg": palette.fg,
        "fg_muted": palette.fg_muted,
        "fg_disabled": palette.fg_disabled,
        "input_bg": palette.input_bg,
        "input_border": palette.input_border,
        "input_focus": palette.input_focus,
        "hover": palette.hover,
        "selected": palette.selected,
        "scrollbar": palette.scrollbar,
        "shadow": palette.shadow,
        "accent": ACCENT,
        "accent_hover": ACCENT_HOVER,
        "accent_pressed": ACCENT_PRESSED,
        "accent_light": ACCENT_LIGHT,
        "danger": DANGER,
        "danger_hover": DANGER_HOVER,
        "success": SUCCESS,
        "warning": WARNING,
        "radius": RADIUS,
        "radius_small": RADIUS_SMALL,
        "spacing": SPACING,
        "margin": MARGIN,
        "font_family": FONT_FAMILY,
        "font_mono": FONT_MONO,
        "font_size": FONT_SIZE_BASE,
        "font_size_small": FONT_SIZE_SMALL,
        "font_size_title": FONT_SIZE_TITLE,
        "font_size_heading": FONT_SIZE_HEADING,
    }
    return template.format(**tokens)
