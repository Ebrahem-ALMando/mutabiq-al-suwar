"""Reusable RTL-safe compound and numeric input controls."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, QSize, Qt
from PySide6.QtGui import QPainter, QPalette, QPen, QPolygonF, QWheelEvent
from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QProxyStyle,
    QSpinBox,
    QStyle,
    QStyleOption,
    QStyleOptionComplex,
    QWidget,
)


class CompoundInputStyle(QProxyStyle):
    """Reserve deterministic, non-overlapping rectangles for compound fields."""

    BUTTON_WIDTH = 32

    def subControlRect(self, control, option, sub_control, widget=None) -> QRect:  # noqa: N802
        rect = option.rect
        if control == QStyle.ComplexControl.CC_SpinBox:
            button_width = min(self.BUTTON_WIDTH, max(26, rect.height() - 10))
            button_left = rect.right() - button_width
            inner_top = rect.top() + 2
            inner_height = max(2, rect.height() - 4)
            upper_height = inner_height // 2
            if sub_control == QStyle.SubControl.SC_SpinBoxUp:
                return QRect(button_left, inner_top, button_width, upper_height)
            if sub_control == QStyle.SubControl.SC_SpinBoxDown:
                return QRect(
                    button_left,
                    inner_top + upper_height,
                    button_width,
                    inner_height - upper_height,
                )
            if sub_control == QStyle.SubControl.SC_SpinBoxEditField:
                return QRect(
                    rect.left() + 10,
                    rect.top() + 2,
                    max(1, rect.width() - button_width - 22),
                    max(1, rect.height() - 4),
                )
        if control == QStyle.ComplexControl.CC_ComboBox:
            button_width = min(36, max(28, rect.height() - 6))
            is_rtl = option.direction == Qt.LayoutDirection.RightToLeft
            if sub_control == QStyle.SubControl.SC_ComboBoxArrow:
                x = rect.left() + 2 if is_rtl else rect.right() - button_width + 1
                return QRect(x, rect.top() + 2, button_width, max(1, rect.height() - 4))
            if sub_control == QStyle.SubControl.SC_ComboBoxEditField:
                if is_rtl:
                    return QRect(
                        rect.left() + button_width + 8,
                        rect.top() + 2,
                        max(1, rect.width() - button_width - 18),
                        max(1, rect.height() - 4),
                    )
                return QRect(
                    rect.left() + 10,
                    rect.top() + 2,
                    max(1, rect.width() - button_width - 18),
                    max(1, rect.height() - 4),
                )
        return super().subControlRect(control, option, sub_control, widget)

    def drawPrimitive(self, element, option: QStyleOption, painter: QPainter, widget=None) -> None:  # noqa: N802
        if element in {
            QStyle.PrimitiveElement.PE_IndicatorArrowUp,
            QStyle.PrimitiveElement.PE_IndicatorArrowDown,
            QStyle.PrimitiveElement.PE_IndicatorArrowLeft,
            QStyle.PrimitiveElement.PE_IndicatorArrowRight,
        }:
            rect = option.rect.adjusted(7, 6, -7, -6)
            center = rect.center()
            half = max(3.0, min(rect.width(), rect.height()) / 2.5)
            if element == QStyle.PrimitiveElement.PE_IndicatorArrowUp:
                points = [
                    QPointF(center.x() - half, center.y() + half / 2),
                    QPointF(center.x(), center.y() - half / 2),
                    QPointF(center.x() + half, center.y() + half / 2),
                ]
            elif element == QStyle.PrimitiveElement.PE_IndicatorArrowDown:
                points = [
                    QPointF(center.x() - half, center.y() - half / 2),
                    QPointF(center.x(), center.y() + half / 2),
                    QPointF(center.x() + half, center.y() - half / 2),
                ]
            elif element == QStyle.PrimitiveElement.PE_IndicatorArrowLeft:
                points = [
                    QPointF(center.x() + half / 2, center.y() - half),
                    QPointF(center.x() - half / 2, center.y()),
                    QPointF(center.x() + half / 2, center.y() + half),
                ]
            else:
                points = [
                    QPointF(center.x() - half / 2, center.y() - half),
                    QPointF(center.x() + half / 2, center.y()),
                    QPointF(center.x() - half / 2, center.y() + half),
                ]
            color = option.palette.color(QPalette.ColorRole.ButtonText)
            if not (option.state & QStyle.StateFlag.State_Enabled):
                color = option.palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText)
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPolyline(QPolygonF(points))
            painter.restore()
            return
        super().drawPrimitive(element, option, painter, widget)

    def sizeFromContents(self, content_type, option, size: QSize, widget=None) -> QSize:  # noqa: N802
        result = super().sizeFromContents(content_type, option, size, widget)
        if content_type in {QStyle.ContentsType.CT_SpinBox, QStyle.ContentsType.CT_ComboBox}:
            result.setHeight(max(44, result.height()))
        if content_type == QStyle.ContentsType.CT_SpinBox:
            result.setWidth(max(140, result.width()))
        return result


def install_compound_input_style(app: QApplication) -> None:
    if getattr(app, "_mutabiq_compound_style", None) is not None:
        return
    proxy = CompoundInputStyle(app.style())
    app.setStyle(proxy)
    app._mutabiq_compound_style = proxy  # type: ignore[attr-defined]


class _NumericMixin:
    def _configure_numeric(self) -> None:
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setMinimumSize(140, 44)
        self.setButtonSymbols(self.ButtonSymbols.UpDownArrows)
        self.setAccelerated(True)
        editor = self.lineEdit()
        editor.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        editor.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        editor.setTextMargins(6, 0, 6, 0)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class NumericSpinBox(_NumericMixin, QSpinBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._configure_numeric()


class NumericDoubleSpinBox(_NumericMixin, QDoubleSpinBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._configure_numeric()


def spin_subcontrol_rects(widget: QSpinBox | QDoubleSpinBox) -> dict[str, QRect]:
    """Expose effective geometry for regression tests and the UI audit page."""
    option = QStyleOptionComplex()
    option.initFrom(widget)
    option.rect = widget.rect()
    style = widget.style()
    return {
        "editor": style.subControlRect(
            QStyle.ComplexControl.CC_SpinBox,
            option,
            QStyle.SubControl.SC_SpinBoxEditField,
            widget,
        ),
        "up": style.subControlRect(QStyle.ComplexControl.CC_SpinBox, option, QStyle.SubControl.SC_SpinBoxUp, widget),
        "down": style.subControlRect(
            QStyle.ComplexControl.CC_SpinBox,
            option,
            QStyle.SubControl.SC_SpinBoxDown,
            widget,
        ),
    }
