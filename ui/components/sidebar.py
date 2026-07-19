"""Formal RTL navigation sidebar with local icons and persisted collapse state."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSettings, QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.icons import icon
from ui.theme import TOKENS


class Sidebar(QFrame):
    pageSelected = Signal(str)

    ITEMS = [
        ("home", "الرئيسية", "house"),
        ("operation", "عملية جديدة", "plus"),
        ("preview", "المعاينة والمطابقة", "images"),
        ("history", "سجل العمليات", "history"),
        ("reports", "التقارير", "file-chart"),
        ("guide", "الدليل التفاعلي", "book-open"),
        ("settings", "الإعدادات", "settings"),
        ("about", "حول البرنامج", "info"),
    ]

    def __init__(self, logo_path: str, reduced_motion: bool = False) -> None:
        super().__init__(objectName="sidebar")
        self.reduced_motion = reduced_motion
        self.settings = QSettings()
        self.expanded = not self.settings.value("sidebar_collapsed", False, type=bool)
        width = TOKENS.sidebar_expanded if self.expanded else TOKENS.sidebar_collapsed
        self.setMinimumWidth(width)
        self.setMaximumWidth(width)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 14)
        layout.setSpacing(6)

        brand_box = QWidget()
        brand_layout = QHBoxLayout(brand_box)
        brand_layout.setContentsMargins(4, 0, 4, 14)
        self.logo = QLabel()
        pixmap = QPixmap(logo_path)
        self.logo.setPixmap(
            pixmap.scaled(
                QSize(58, 50),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.logo.setFixedSize(58, 50)
        self.brand = QLabel("مُطابق الصور", objectName="productName")
        self.brand.setToolTip("مُطابق الصور")
        brand_layout.addWidget(self.logo)
        brand_layout.addWidget(self.brand, 1)
        layout.addWidget(brand_box)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}
        for key, label, icon_name in self.ITEMS:
            button = QPushButton(label, objectName="navButton")
            button.setProperty("icon_name", icon_name)
            button.setCheckable(True)
            button.setIconSize(QSize(20, 20))
            button.setToolTip(label)
            button.setAccessibleName(label)
            button.clicked.connect(lambda checked=False, page=key: self.pageSelected.emit(page))
            self.group.addButton(button)
            self.buttons[key] = button
            layout.addWidget(button)
        layout.addStretch(1)
        self.collapse_button = QPushButton("طي الشريط", objectName="navButton")
        self.collapse_button.setProperty("icon_name", "panel-right")
        self.collapse_button.setToolTip("طي الشريط الجانبي أو توسيعه")
        self.collapse_button.clicked.connect(self.toggle)
        layout.addWidget(self.collapse_button)
        self._sync_labels()
        self.set_theme("light")
        self.buttons["home"].setChecked(True)

    def set_theme(self, theme: str) -> None:
        for button in (*self.buttons.values(), self.collapse_button):
            button.setIcon(icon(button.property("icon_name"), theme=theme, size=20, role="nav_text"))

    def _sync_labels(self) -> None:
        for key, label, _ in self.ITEMS:
            self.buttons[key].setText(label if self.expanded else "")
        self.brand.setVisible(self.expanded)
        self.collapse_button.setText("طي الشريط" if self.expanded else "")

    def toggle(self) -> None:
        self.expanded = not self.expanded
        self.settings.setValue("sidebar_collapsed", not self.expanded)
        target = TOKENS.sidebar_expanded if self.expanded else TOKENS.sidebar_collapsed
        self._sync_labels()
        if self.reduced_motion:
            self.setMinimumWidth(target)
            self.setMaximumWidth(target)
            return
        self.setMinimumWidth(TOKENS.sidebar_collapsed)
        self._animation = QPropertyAnimation(self, b"maximumWidth", self)
        self._animation.setDuration(210)
        self._animation.setStartValue(self.width())
        self._animation.setEndValue(target)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.finished.connect(lambda: self.setMinimumWidth(target))
        self._animation.start()

    def select(self, key: str) -> None:
        if key in self.buttons:
            self.buttons[key].setChecked(True)
