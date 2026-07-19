"""Theme-aware, clipping-safe local SVG icon registry.

Lucide SVGs are rendered into an inset, aspect-ratio-preserving target.  The
cache key includes icon, color, logical size, device ratio and inset so the
same path is safe at every supported Windows scale factor.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from ui.theme import colors_for

_ROOT = Path(__file__).resolve().parents[1] / "assets" / "icons" / "lucide"


@dataclass(frozen=True, slots=True)
class SvgMetadata:
    name: str
    view_box: QRectF
    valid: bool


def svg_metadata(name: str) -> SvgMetadata:
    path = _ROOT / f"{name}.svg"
    renderer = QSvgRenderer(str(path))
    return SvgMetadata(name, renderer.viewBoxF(), path.is_file() and renderer.isValid())


def icon_names() -> tuple[str, ...]:
    return tuple(sorted(path.stem for path in _ROOT.glob("*.svg")))


@lru_cache(maxsize=1024)
def _pixmap(name: str, color: str, size: int, ratio: float, inset: float) -> QPixmap:
    path = _ROOT / f"{name}.svg"
    if not path.exists():
        path = _ROOT / "circle-help.svg"
    source = path.read_text(encoding="utf-8").replace("currentColor", QColor(color).name())
    renderer = QSvgRenderer(QByteArray(source.encode("utf-8")))
    physical_size = max(1, round(size * ratio))
    result = QPixmap(physical_size, physical_size)
    result.fill(Qt.GlobalColor.transparent)
    if not renderer.isValid() or renderer.viewBoxF().isEmpty():
        result.setDevicePixelRatio(ratio)
        return result

    safe = max(2.0, inset * ratio)
    available = max(1.0, physical_size - safe * 2.0)
    view_box = renderer.viewBoxF()
    scale = min(available / view_box.width(), available / view_box.height())
    target_width = view_box.width() * scale
    target_height = view_box.height() * scale
    target = QRectF(
        (physical_size - target_width) / 2.0,
        (physical_size - target_height) / 2.0,
        target_width,
        target_height,
    )
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
    renderer.render(painter, target)
    painter.end()
    result.setDevicePixelRatio(ratio)
    return result


def icon_pixmap(
    name: str,
    *,
    color: str,
    size: int = 20,
    ratio: float = 1.0,
    inset: float = 2.5,
) -> QPixmap:
    """Return an inset, DPR-aware pixmap suitable for custom-painted controls."""
    return _pixmap(name, QColor(color).name(), size, ratio, inset)


def icon(
    name: str,
    *,
    theme: str = "light",
    size: int = 20,
    role: str = "text_primary",
    color: str | None = None,
) -> QIcon:
    """Return a crisp semantic SVG icon with a safe local fallback."""
    resolved = color or colors_for(theme).get(role, colors_for(theme)["text_primary"])
    result = QIcon()
    for ratio in (1.0, 1.25, 1.5, 1.75, 2.0):
        result.addPixmap(_pixmap(name, QColor(resolved).name(), size, ratio, 2.5))
    return result


def logo_icon() -> QIcon:
    root = Path(__file__).resolve().parents[1]
    png = root / "assets" / "branding" / "official_logo.png"
    return QIcon(str(png))


def clear_icon_cache() -> None:
    _pixmap.cache_clear()
