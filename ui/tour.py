"""Optional, resilient overlay tour that never blocks the workflow."""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class TourOverlay(QWidget):
    def __init__(self, window, steps: list[tuple[str, str]]) -> None:
        super().__init__(window)
        self.window = window
        self.steps = steps
        self.index = 0
        self.target_rect = QRect()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setObjectName("tourOverlay")
        self.card = QFrame(self, objectName="dialogPanel")
        box = QVBoxLayout(self.card)
        self.counter = QLabel(objectName="eyebrow")
        self.title = QLabel(objectName="sectionTitle")
        self.detail = QLabel(objectName="muted")
        self.detail.setWordWrap(True)
        buttons = QHBoxLayout()
        self.skip = QPushButton("تخطي")
        self.back = QPushButton("السابق")
        self.next = QPushButton("التالي", objectName="primary")
        self.skip.clicked.connect(self.close)
        self.back.clicked.connect(lambda: self.show_step(self.index - 1))
        self.next.clicked.connect(lambda: self.show_step(self.index + 1))
        buttons.addWidget(self.skip)
        buttons.addStretch()
        buttons.addWidget(self.back)
        buttons.addWidget(self.next)
        box.addWidget(self.counter)
        box.addWidget(self.title)
        box.addWidget(self.detail)
        box.addLayout(buttons)
        self.resize(window.size())
        self.show_step(0)

    def show_step(self, index: int) -> None:
        if index >= len(self.steps):
            self.close()
            return
        self.index = max(0, index)
        object_name, title = self.steps[self.index]
        target = self.window.findChild(QWidget, object_name)
        self.target_rect = QRect()
        if target and target.isVisible():
            top_left = target.mapTo(self, target.rect().topLeft())
            self.target_rect = QRect(top_left, target.size()).adjusted(-6, -6, 6, 6)
        self.counter.setText(f"الخطوة {self.index + 1} من {len(self.steps)}")
        self.title.setText(title)
        self.detail.setText("اتبع العنصر المضاء. يمكنك الرجوع أو التخطي في أي وقت دون تغيير بياناتك.")
        self.back.setEnabled(self.index > 0)
        self.next.setText("إنهاء" if self.index == len(self.steps) - 1 else "التالي")
        x = 24 if self.target_rect.center().x() > self.width() // 2 else max(24, self.width() - 384)
        self.card.setGeometry(x, max(24, self.height() - 238), 360, 200)
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(3, 45, 35, 175))
        if not self.target_rect.isNull():
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(self.target_rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor("#E2C992"), 3))
            painter.drawRoundedRect(self.target_rect, 10, 10)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Right):
            self.show_step(self.index + 1)
        elif event.key() == Qt.Key.Key_Left:
            self.show_step(self.index - 1)
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "card"):
            self.show_step(self.index)
