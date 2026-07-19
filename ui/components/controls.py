"""Reusable premium controls shared by the shell and workflow pages."""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.icons import icon
from ui.theme import colors_for


class ThemeToggle(QAbstractButton):
    themeChanged = Signal(str)

    def __init__(self, theme: str = "light", reduced_motion: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._theme = theme
        self._position = 0.0 if theme == "light" else 1.0
        self.reduced_motion = reduced_motion
        self.setObjectName("themeToggle")
        self.setFixedSize(74, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("التبديل بين السمة الفاتحة والداكنة")
        self.setAccessibleName("تبديل السمة")
        self.clicked.connect(self.toggle_theme)

    def get_position(self) -> float:
        return self._position

    def set_position(self, value: float) -> None:
        self._position = value
        self.update()

    position = Property(float, get_position, set_position)

    def set_theme(self, theme: str, animate: bool = False) -> None:
        self._theme = "dark" if theme == "dark" else "light"
        target = 1.0 if self._theme == "dark" else 0.0
        if not animate or self.reduced_motion:
            self.set_position(target)
            return
        self._animation = QPropertyAnimation(self, b"position", self)
        self._animation.setDuration(210)
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(target)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()

    def toggle_theme(self) -> None:
        next_theme = "dark" if self._theme == "light" else "light"
        self.set_theme(next_theme, True)
        self.themeChanged.emit(next_theme)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.toggle_theme()
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:
        del event
        c = colors_for(self._theme)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = QRectF(1, 1, self.width() - 2, self.height() - 2)
        painter.setPen(QPen(QColor(c["border_default"]), 1))
        painter.setBrush(QColor(c["secondary"]))
        painter.drawRoundedRect(track, 17, 17)
        knob_x = 4 + self._position * (self.width() - 36)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(c["surface_primary"]))
        painter.drawEllipse(QRectF(knob_x, 4, 28, 28))
        sun = icon("sun", theme=self._theme, size=16, role="gold").pixmap(16, 16)
        moon = icon("moon", theme=self._theme, size=16, role="primary").pixmap(16, 16)
        painter.drawPixmap(10, 10, sun)
        painter.drawPixmap(self.width() - 26, 10, moon)


class SegmentedControl(QFrame):
    changed = Signal(int)

    def __init__(self, labels: list[tuple[str, str]], parent=None) -> None:
        super().__init__(parent, objectName="segmented")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: list[QPushButton] = []
        for index, (label, icon_name) in enumerate(labels):
            button = QPushButton(label, objectName="segmentButton")
            button.setCheckable(True)
            button.setProperty("icon_name", icon_name)
            button.clicked.connect(lambda checked=False, i=index: self.changed.emit(i))
            self.group.addButton(button, index)
            self.buttons.append(button)
            layout.addWidget(button)
        self.buttons[0].setChecked(True)

    def set_theme(self, theme: str) -> None:
        for button in self.buttons:
            button.setIcon(icon(button.property("icon_name"), theme=theme, size=18))

    def set_index(self, index: int) -> None:
        if 0 <= index < len(self.buttons):
            self.buttons[index].setChecked(True)


class EmptyState(QWidget):
    actionRequested = Signal()

    def __init__(self, title: str, detail: str, action: str = "", icon_name: str = "inbox", parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image = QLabel()
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setProperty("icon_name", icon_name)
        self.title = QLabel(title, objectName="emptyTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail = QLabel(detail, objectName="muted")
        self.detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail.setWordWrap(True)
        layout.addWidget(self.image)
        layout.addWidget(self.title)
        layout.addWidget(self.detail)
        if action:
            button = QPushButton(action, objectName="primary")
            button.clicked.connect(self.actionRequested)
            layout.addWidget(button, 0, Qt.AlignmentFlag.AlignCenter)

    def set_theme(self, theme: str) -> None:
        self.image.setPixmap(icon(self.image.property("icon_name"), theme=theme, size=48, role="gold").pixmap(48, 48))
