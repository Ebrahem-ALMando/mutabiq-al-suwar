"""RTL sidebar with one reusable, fully interactive navigation-row control."""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRect, QSettings, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFocusEvent, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QAbstractButton, QButtonGroup, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.icons import icon_pixmap
from ui.theme import TOKENS, colors_for


def _blend(first: QColor, second: QColor, amount: float) -> QColor:
    amount = max(0.0, min(1.0, amount))
    return QColor(
        round(first.red() + (second.red() - first.red()) * amount),
        round(first.green() + (second.green() - first.green()) * amount),
        round(first.blue() + (second.blue() - first.blue()) * amount),
        round(first.alpha() + (second.alpha() - first.alpha()) * amount),
    )


class SidebarNavItem(QAbstractButton):
    """Single hit target with explicit active, hover, focus and collapsed states."""

    def __init__(self, label: str, icon_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.icon_name = icon_name
        self._theme = "light"
        self._collapsed = False
        self._hover_progress = 0.0
        self._reduced_motion = False
        self.setText(label)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setMinimumHeight(48)
        self.setMaximumHeight(48)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setAccessibleName(label)
        self.setToolTip(label)
        self.toggled.connect(lambda _checked: self._state_changed())

    @Property(bool)
    def active(self) -> bool:
        return self.isChecked()

    @Property(bool)
    def hovered(self) -> bool:
        return self.underMouse() or self._hover_progress > 0.01

    @Property(bool)
    def keyboardFocused(self) -> bool:  # noqa: N802 - Qt property naming
        return self.hasFocus()

    @Property(bool)
    def collapsed(self) -> bool:
        return self._collapsed

    def get_hover_progress(self) -> float:
        return self._hover_progress

    def set_hover_progress(self, value: float) -> None:
        self._hover_progress = value
        self.update()

    hoverProgress = Property(float, get_hover_progress, set_hover_progress)  # noqa: N815

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self._state_changed()

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self.setProperty("collapsed", collapsed)
        self.updateGeometry()
        self.update()

    def set_reduced_motion(self, enabled: bool) -> None:
        self._reduced_motion = enabled

    def _state_changed(self) -> None:
        for name, value in (
            ("active", self.active),
            ("hovered", self.hovered),
            ("keyboardFocused", self.keyboardFocused),
        ):
            self.setProperty(name, value)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _animate_hover(self, target: float) -> None:
        self.setProperty("hovered", bool(target))
        if self._reduced_motion:
            self.set_hover_progress(target)
            self._state_changed()
            return
        if hasattr(self, "_hover_animation"):
            self._hover_animation.stop()
        self._hover_animation = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_animation.setDuration(160)
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(target)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_animation.start()

    def enterEvent(self, event) -> None:
        self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animate_hover(0.0)
        super().leaveEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:
        super().focusInEvent(event)
        self._state_changed()

    def focusOutEvent(self, event: QFocusEvent) -> None:
        super().focusOutEvent(event)
        self._state_changed()

    def resolved_state_colors(self) -> dict[str, QColor]:
        c = colors_for(self._theme)
        base = QColor(c["nav_background"])
        hover = QColor("#0F5C4D" if self._theme == "dark" else "#0A5548")
        if self.active:
            active = QColor("#0A4A3E" if self._theme == "dark" else "#F0EDE7")
            active_hover = QColor("#146B5A" if self._theme == "dark" else "#E8E4DC")
            return {
                "background": _blend(active, active_hover, self._hover_progress),
                "text": QColor(c["gold"] if self._theme == "dark" else "#054239"),
                "icon": QColor(c["gold"] if self._theme == "dark" else "#054239"),
                "indicator": QColor(c["gold"]),
            }
        return {
            "background": _blend(base, hover, self._hover_progress),
            "text": QColor(c["nav_text"]),
            "icon": QColor(c["gold"] if self._hover_progress > 0.01 else c["nav_text"]),
            "indicator": QColor(c["gold"]),
        }

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self.setProperty("hovered", True)
        super().mouseMoveEvent(event)

    def sizeHint(self) -> QSize:
        return QSize(TOKENS.sidebar_collapsed if self._collapsed else TOKENS.sidebar_expanded - 24, 48)

    def content_rects(self) -> dict[str, QRect]:
        """Return the logical icon/text geometry used for painting and regression tests."""

        rect = self.rect().adjusted(1, 1, -1, -1)
        icon_container = 28
        right = rect.right() - 12 - (4 if self.active else 0)
        icon_x = right - icon_container + 1
        if self._collapsed:
            icon_x = rect.center().x() - icon_container // 2
        icon_rect = QRect(icon_x, rect.center().y() - icon_container // 2, icon_container, icon_container)
        text_rect = QRect()
        if not self._collapsed and self.text():
            text_rect = rect.adjusted(14, 0, -(rect.right() - icon_x + 8), 0)
        return {"icon": icon_rect, "text": text_rect}

    def paintEvent(self, event) -> None:
        del event
        c = colors_for(self._theme)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)

        state_colors = self.resolved_state_colors()
        background = state_colors["background"]
        text_color = state_colors["text"]
        icon_color = state_colors["icon"]

        if not self.isEnabled():
            text_color = QColor(c["text_disabled"])
            icon_color = QColor(c["text_disabled"])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(rect, 9, 9)

        if self.active:
            painter.setBrush(state_colors["indicator"])
            indicator = rect.adjusted(rect.width() - 4, 7, 0, -7)
            painter.drawRoundedRect(indicator, 2, 2)

        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(c["border_focus"]), 2))
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 8, 8)

        content = self.content_rects()
        icon_rect = content["icon"]
        icon_container = icon_rect.width()
        visual_size = 26
        ratio = max(1.0, self.devicePixelRatioF())
        pixmap = icon_pixmap(
            self.icon_name,
            color=icon_color.name(),
            size=visual_size,
            ratio=ratio,
        )
        icon_x = icon_rect.x() + (icon_container - visual_size) // 2
        icon_y = icon_rect.y() + (icon_container - visual_size) // 2
        painter.drawPixmap(icon_x, icon_y, pixmap)

        if not self._collapsed and self.text():
            text_rect = content["text"]
            font = painter.font()
            font.setBold(self.active)
            painter.setFont(font)
            painter.setPen(text_color)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.text())


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
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.reduced_motion = reduced_motion
        self.settings = QSettings()
        self.expanded = not self.settings.value("sidebar_collapsed", False, type=bool)
        width = TOKENS.sidebar_expanded if self.expanded else TOKENS.sidebar_collapsed
        self.setMinimumWidth(width)
        self.setMaximumWidth(width)
        layout = QVBoxLayout(self)
        layout.setDirection(QVBoxLayout.Direction.TopToBottom)
        layout.setContentsMargins(12, 16, 12, 14)
        layout.setSpacing(6)

        brand_box = QWidget()
        brand_box.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        brand_layout = QHBoxLayout(brand_box)
        brand_layout.setDirection(QHBoxLayout.Direction.RightToLeft)
        brand_layout.setContentsMargins(4, 0, 4, 14)
        self.logo = QLabel()
        pixmap = QPixmap(logo_path)
        self.logo.setPixmap(
            pixmap.scaled(QSize(58, 50), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )
        self.logo.setFixedSize(58, 50)
        self.brand = QLabel("مُطابق الصور", objectName="productName")
        self.brand.setToolTip("مُطابق الصور")
        brand_layout.addWidget(self.logo)
        brand_layout.addWidget(self.brand, 1)
        layout.addWidget(brand_box)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[str, SidebarNavItem] = {}
        for key, label, icon_name in self.ITEMS:
            button = SidebarNavItem(label, icon_name, self)
            button.setObjectName(f"nav_{key}")
            button.setProperty("page_key", key)
            button.set_reduced_motion(reduced_motion)
            button.clicked.connect(lambda checked=False, page=key: self.pageSelected.emit(page))
            self.group.addButton(button)
            self.buttons[key] = button
            layout.addWidget(button)
        layout.addStretch(1)
        self.collapse_button = SidebarNavItem("طي الشريط", "panel-right", self)
        self.collapse_button.setObjectName("sidebarCollapse")
        self.collapse_button.setCheckable(False)
        self.collapse_button.set_reduced_motion(reduced_motion)
        self.collapse_button.clicked.connect(self.toggle)
        layout.addWidget(self.collapse_button)
        self._sync_collapsed()
        self.set_theme("light")
        self.buttons["home"].setChecked(True)

    def set_theme(self, theme: str) -> None:
        for button in (*self.buttons.values(), self.collapse_button):
            button.set_theme(theme)

    def set_reduced_motion(self, enabled: bool) -> None:
        self.reduced_motion = enabled
        for button in (*self.buttons.values(), self.collapse_button):
            button.set_reduced_motion(enabled)

    def _sync_collapsed(self) -> None:
        collapsed = not self.expanded
        self.brand.setVisible(self.expanded)
        for button in (*self.buttons.values(), self.collapse_button):
            button.set_collapsed(collapsed)

    def toggle(self) -> None:
        self.expanded = not self.expanded
        self.settings.setValue("sidebar_collapsed", not self.expanded)
        target = TOKENS.sidebar_expanded if self.expanded else TOKENS.sidebar_collapsed
        self._sync_collapsed()
        if self.reduced_motion:
            self.setMinimumWidth(target)
            self.setMaximumWidth(target)
            return
        self.setMinimumWidth(TOKENS.sidebar_collapsed)
        self._animation = QPropertyAnimation(self, b"maximumWidth", self)
        self._animation.setDuration(180)
        self._animation.setStartValue(self.width())
        self._animation.setEndValue(target)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.finished.connect(lambda: self.setMinimumWidth(target))
        self._animation.start()

    def select(self, key: str) -> None:
        if key in self.buttons:
            self.buttons[key].setChecked(True)
