"""Reusable, RTL, theme-aware application dialogs."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class AppDialog(QDialog):
    """Consistent replacement for native message boxes used by the app."""

    actionTriggered = Signal(str)

    def __init__(
        self,
        title: str,
        message: str,
        *,
        severity: str = "info",
        details: str = "",
        primary_text: str = "إغلاق",
        secondary_text: str = "",
        destructive_text: str = "",
        log_path: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.details_text = details
        self.log_path = log_path
        self.selected_action = ""
        self.setObjectName("appDialog")
        self.setWindowTitle(title)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumWidth(520)
        self.setMaximumWidth(820)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(14)

        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        heading.setProperty("severity", severity)
        heading.setWordWrap(True)
        root.addWidget(heading)
        body = QLabel(message)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(body)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlainText(details)
        self.details.setMinimumHeight(130)
        self.details.setVisible(False)
        root.addWidget(self.details)

        auxiliary = QHBoxLayout()
        if details:
            details_button = QPushButton("عرض التفاصيل")
            details_button.clicked.connect(lambda: self._toggle_details(details_button))
            auxiliary.addWidget(details_button)
            copy_button = QPushButton("نسخ التفاصيل")
            copy_button.clicked.connect(self.copy_details)
            auxiliary.addWidget(copy_button)
        if log_path:
            log_button = QPushButton("فتح السجل")
            log_button.clicked.connect(lambda: self._emit_action("open_log"))
            auxiliary.addWidget(log_button)
        auxiliary.addStretch()
        root.addLayout(auxiliary)

        actions = QHBoxLayout()
        actions.addStretch()
        if destructive_text:
            destructive = QPushButton(destructive_text)
            destructive.setProperty("severity", "error")
            destructive.setDefault(not bool(primary_text))
            destructive.clicked.connect(lambda: self._finish("destructive", QDialog.DialogCode.Accepted))
            actions.addWidget(destructive)
        if secondary_text:
            secondary = QPushButton(secondary_text)
            secondary.clicked.connect(lambda: self._finish("secondary", QDialog.DialogCode.Rejected))
            actions.addWidget(secondary)
        if primary_text:
            primary = QPushButton(primary_text)
            primary.setObjectName("primary")
            primary.setDefault(True)
            primary.clicked.connect(lambda: self._finish("primary", QDialog.DialogCode.Accepted))
            actions.addWidget(primary)
        root.addLayout(actions)

    def _toggle_details(self, button: QPushButton) -> None:
        visible = not self.details.isVisible()
        self.details.setVisible(visible)
        button.setText("إخفاء التفاصيل" if visible else "عرض التفاصيل")
        self.adjustSize()

    def copy_details(self) -> None:
        QGuiApplication.clipboard().setText(self.details_text)

    def _emit_action(self, action: str) -> None:
        self.actionTriggered.emit(action)

    def _finish(self, action: str, code: QDialog.DialogCode) -> None:
        self.selected_action = action
        self.actionTriggered.emit(action)
        self.done(code)


def confirm_dialog(
    parent: QWidget,
    title: str,
    message: str,
    *,
    confirm_text: str = "متابعة",
    cancel_text: str = "عدم المتابعة",
    destructive: bool = False,
) -> bool:
    dialog = AppDialog(
        title,
        message,
        severity="warning",
        primary_text="" if destructive else confirm_text,
        secondary_text=cancel_text,
        destructive_text=confirm_text if destructive else "",
        parent=parent,
    )
    dialog.exec()
    return dialog.selected_action in {"primary", "destructive"}


def message_dialog(
    parent: QWidget | None,
    title: str,
    message: str,
    *,
    severity: str = "info",
    details: str = "",
    log_path: Path | None = None,
) -> AppDialog:
    return AppDialog(title, message, severity=severity, details=details, log_path=log_path, parent=parent)
