"""Wrap the supplied favicon image in a valid Windows ICO container."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    source = root / "assets" / "branding" / "official_favicon_source.ico"
    target = root / "assets" / "icons" / "app.ico"
    _app = QApplication.instance() or QApplication([])
    supplied = QImage(str(source))
    if supplied.isNull():
        print("The supplied official favicon cannot be decoded", file=sys.stderr)
        return 1
    canvas = QImage(256, 256, QImage.Format.Format_ARGB32)
    canvas.fill(Qt.GlobalColor.transparent)
    scaled = supplied.scaled(
        244,
        244,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    painter = QPainter(canvas)
    painter.drawImage((256 - scaled.width()) // 2, (256 - scaled.height()) // 2, scaled)
    painter.end()
    if not canvas.save(str(target), "ICO"):
        print("Qt ICO writer is unavailable", file=sys.stderr)
        return 1
    if target.read_bytes()[:4] != b"\x00\x00\x01\x00":
        print("Generated app.ico has an invalid ICO header", file=sys.stderr)
        return 1
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
