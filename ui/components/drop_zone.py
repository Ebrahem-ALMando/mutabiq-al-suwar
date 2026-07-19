"""منطقة سحب وإفلات مدركة لنوع المدخل."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class DropZone(QFrame):
    """تقبل ملف بيانات أو مجلداً وتعرض حالة صريحة."""

    pathDropped = Signal(object)

    def __init__(self, title: str, kind: str, extensions: set[str] | None = None) -> None:
        super().__init__(objectName="dropZone")
        self.kind = kind
        self.extensions = extensions or set()
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        self.setProperty("dragState", "rest")
        layout = QVBoxLayout(self)
        self.title = QLabel(title)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet("font-weight:700")
        self.detail = QLabel("اسحب هنا أو استخدم زر الاختيار")
        self.detail.setObjectName("muted")
        self.detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail.setWordWrap(True)
        layout.addWidget(self.title)
        layout.addWidget(self.detail)

    def valid(self, path: Path) -> bool:
        return path.is_dir() if self.kind == "folder" else path.is_file() and path.suffix.lower() in self.extensions

    def set_path(self, path: Path | None) -> None:
        self.detail.setText(str(path) if path else "اسحب هنا أو استخدم زر الاختيار")
        self.setProperty("dragState", "selected" if path else "rest")
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        state = "valid" if len(paths) == 1 and self.valid(paths[0]) else "invalid"
        self.setProperty("dragState", state)
        self.style().unpolish(self)
        self.style().polish(self)
        event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        self.setProperty("dragState", "rest")
        self.style().unpolish(self)
        self.style().polish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if len(paths) == 1 and self.valid(paths[0]):
            self.set_path(paths[0])
            self.pathDropped.emit(paths[0])
            event.acceptProposedAction()
        else:
            self.detail.setText("العنصر غير مدعوم. تحقق من النوع أو الامتداد.")
            event.ignore()
