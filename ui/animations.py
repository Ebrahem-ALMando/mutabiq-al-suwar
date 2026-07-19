"""Short, reusable and reduced-motion-aware UI animations."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QObject, QPropertyAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


class AnimationManager(QObject):
    def __init__(self, reduced_motion: bool = False, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.reduced_motion = reduced_motion
        self._active: dict[int, QPropertyAnimation] = {}

    def set_reduced_motion(self, enabled: bool) -> None:
        self.reduced_motion = enabled
        if enabled:
            for animation in tuple(self._active.values()):
                animation.stop()
            self._active.clear()

    def fade_in(self, widget: QWidget, duration: int = 210) -> None:
        if self.reduced_motion or not widget.isVisible():
            return
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        animation = QPropertyAnimation(effect, b"opacity", widget)
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        key = id(widget)
        self._active[key] = animation
        animation.finished.connect(lambda: self._active.pop(key, None))
        animation.start()
