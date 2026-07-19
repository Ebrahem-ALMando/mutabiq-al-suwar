"""شريط تنقل RTL قابل للطي مع انتقال قصير."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QButtonGroup, QFrame, QLabel, QPushButton, QStyle, QVBoxLayout


class Sidebar(QFrame):
    pageSelected = Signal(str)

    ITEMS = [
        ("home", "الرئيسية", QStyle.StandardPixmap.SP_ComputerIcon),
        ("operation", "عملية جديدة", QStyle.StandardPixmap.SP_FileDialogNewFolder),
        ("preview", "المعاينة والمطابقة", QStyle.StandardPixmap.SP_FileDialogContentsView),
        ("history", "سجل العمليات", QStyle.StandardPixmap.SP_FileDialogDetailedView),
        ("reports", "التقارير", QStyle.StandardPixmap.SP_FileIcon),
        ("settings", "الإعدادات", QStyle.StandardPixmap.SP_FileDialogInfoView),
        ("about", "حول البرنامج", QStyle.StandardPixmap.SP_MessageBoxInformation),
    ]

    def __init__(self, logo_path: str, reduced_motion: bool = False) -> None:
        super().__init__(objectName="sidebar")
        self.expanded = True
        self.reduced_motion = reduced_motion
        self.setMinimumWidth(238)
        self.setMaximumWidth(238)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 16, 10, 12)
        brand = QLabel("مُطابق الصور", objectName="productName")
        brand.setPixmap(QIcon(logo_path).pixmap(QSize(38, 38)))
        brand.setToolTip("مُطابق الصور")
        layout.addWidget(brand)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}
        for key, text, icon in self.ITEMS:
            button = QPushButton(text, objectName="navButton")
            button.setIcon(self.style().standardIcon(icon))
            button.setCheckable(True)
            button.setToolTip(text)
            button.clicked.connect(lambda checked=False, page=key: self.pageSelected.emit(page))
            self.group.addButton(button)
            self.buttons[key] = button
            layout.addWidget(button)
        layout.addStretch()
        self.collapse_button = QPushButton("طي الشريط", objectName="navButton")
        self.collapse_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self.collapse_button.clicked.connect(self.toggle)
        layout.addWidget(self.collapse_button)
        self.buttons["home"].setChecked(True)

    def toggle(self) -> None:
        self.expanded = not self.expanded
        target = 238 if self.expanded else 68
        for key, button in self.buttons.items():
            label = next(item[1] for item in self.ITEMS if item[0] == key)
            button.setText(label if self.expanded else "")
        self.collapse_button.setText("طي الشريط" if self.expanded else "")
        if self.reduced_motion:
            self.setMinimumWidth(target)
            self.setMaximumWidth(target)
            return
        self.animation = QPropertyAnimation(self, b"maximumWidth", self)
        self.animation.setDuration(180)
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(target)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()
        self.setMinimumWidth(target)

    def select(self, key: str) -> None:
        if key in self.buttons:
            self.buttons[key].setChecked(True)
