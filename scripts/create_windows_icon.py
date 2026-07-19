"""حوّل شعار SVG المحلي إلى أيقونة Windows متعددة الدقة عبر Qt."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    source = root / "assets" / "icons" / "app_logo.svg"
    target = root / "assets" / "icons" / "app.ico"
    _app = QApplication.instance() or QApplication([])
    renderer = QSvgRenderer(str(source))
    image = QImage(256, 256, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    renderer.render(painter, QRectF(0, 0, 256, 256))
    painter.end()
    if not image.save(str(target), "ICO"):
        print("Qt ICO plugin is unavailable", file=sys.stderr)
        return 1
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
