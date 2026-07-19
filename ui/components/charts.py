"""رسوم Qt خفيفة بلا مؤثرات ثلاثية الأبعاد."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

from ui.theme import colors_for


def _theme_color(token: str) -> QColor:
    app = QApplication.instance()
    theme = str(app.property("active_theme") or "light") if app else "light"
    contrast = bool(app.property("high_contrast")) if app else False
    return QColor(colors_for(theme, contrast).get(token, token))


class DonutChart(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.values: list[tuple[str, int, str]] = []
        self.setMinimumSize(240, 180)

    def set_values(self, values: list[tuple[str, int, str]]) -> None:
        self.values = values
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        total = sum(value for _, value, _ in self.values)
        if not total:
            painter.setPen(_theme_color("text_muted"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "لا توجد بيانات بعد")
            return
        size = min(self.width(), self.height()) - 56
        rect = QRectF(18, (self.height() - size) / 2, size, size)
        start = 90 * 16
        for _label, value, color in self.values:
            span = -int(value / total * 360 * 16)
            painter.setPen(QPen(_theme_color(color), 18, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            painter.drawArc(rect, start, span)
            start += span
        x = size + 35
        y = 35
        for label, value, color in self.values:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_theme_color(color))
            painter.drawEllipse(x, y, 10, 10)
            painter.setPen(self.palette().text().color())
            painter.drawText(x + 16, y + 10, f"{label}: {value}")
            y += 25


class BarChart(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.values: list[tuple[str, int]] = []
        self.setMinimumHeight(170)

    def set_values(self, values: list[tuple[str, int]]) -> None:
        self.values = values
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.values or max((value for _, value in self.values), default=0) == 0:
            painter.setPen(_theme_color("text_muted"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "لا توجد بيانات بعد")
            return
        maximum = max(value for _, value in self.values)
        width = max(12, (self.width() - 40) / len(self.values) - 8)
        for index, (label, value) in enumerate(self.values):
            height = (self.height() - 52) * value / maximum
            x = 20 + index * (width + 8)
            painter.setBrush(_theme_color("primary"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(x, self.height() - 30 - height, width, height), 4, 4)
            painter.setPen(self.palette().text().color())
            painter.drawText(
                QRectF(x - 10, self.height() - 26, width + 20, 20), Qt.AlignmentFlag.AlignCenter, label[:8]
            )
