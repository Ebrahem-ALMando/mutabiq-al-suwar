"""Theme-aware local SVG icon registry.

The line icons are derived from Lucide (ISC); only the paths used by the app are
shipped.  Rendering is cached and never depends on the operating-system theme.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from ui.theme import colors_for

_ROOT = Path(__file__).resolve().parents[1] / "assets" / "icons" / "lucide"


@lru_cache(maxsize=256)
def _pixmap(name: str, color: str, size: int, ratio: float) -> QPixmap:
    path = _ROOT / f"{name}.svg"
    if not path.exists():
        path = _ROOT / "circle-help.svg"
    source = path.read_text(encoding="utf-8").replace("currentColor", QColor(color).name())
    px = max(1, round(size * ratio))
    result = QPixmap(px, px)
    result.setDevicePixelRatio(ratio)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(QByteArray(source.encode("utf-8"))).render(painter)
    painter.end()
    return result


def icon(name: str, *, theme: str = "light", size: int = 20, role: str = "text_primary") -> QIcon:
    """Return a crisp, semantic SVG icon with a safe fallback."""
    color = colors_for(theme).get(role, colors_for(theme)["text_primary"])
    result = QIcon()
    for ratio in (1.0, 1.5, 2.0):
        pixmap = _pixmap(name, color, size, ratio)
        result.addPixmap(pixmap, QIcon.Mode.Normal, QIcon.State.Off)
    return result


def logo_icon() -> QIcon:
    root = Path(__file__).resolve().parents[1]
    png = root / "assets" / "branding" / "official_logo.png"
    # The authoritative SVG is shipped unchanged, but it embeds a raster data
    # URI unsupported by QtSvg on some Windows builds. The supplied PNG is its
    # byte-for-byte official fallback and renders consistently.
    return QIcon(str(png))


def clear_icon_cache() -> None:
    _pixmap.cache_clear()
