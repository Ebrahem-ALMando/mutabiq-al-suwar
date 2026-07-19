"""منطقة سحب وإفلات مدركة لنوع المدخل."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from ui.bidi import elide_middle
from ui.icons import icon


class DropZone(QFrame):
    """تقبل ملف بيانات أو مجلداً وتعرض حالة صريحة."""

    pathDropped = Signal(object)

    def __init__(self, title: str, kind: str, extensions: set[str] | None = None) -> None:
        super().__init__(objectName="dropZone")
        self.kind = kind
        self.extensions = extensions or set()
        self.setAcceptDrops(True)
        self.setMinimumHeight(84)
        self.setProperty("dragState", "rest")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(QSize(34, 34))
        self.icon_label.setProperty("icon_name", "file-chart" if kind == "file" else "inbox")
        layout.addWidget(self.icon_label)
        text = QVBoxLayout()
        self.title = QLabel(title)
        self.title.setStyleSheet("font-weight:700")
        self.detail = QLabel("اسحب هنا أو استخدم زر الاختيار")
        self.detail.setObjectName("muted")
        self.detail.setWordWrap(True)
        text.addWidget(self.title)
        text.addWidget(self.detail)
        layout.addLayout(text, 1)
        self.set_theme("light")

    def valid(self, path: Path) -> bool:
        return path.is_dir() if self.kind == "folder" else path.is_file() and path.suffix.lower() in self.extensions

    def set_path(self, path: Path | None) -> None:
        self.detail.setText(elide_middle(path) if path else "اسحب هنا أو استخدم زر الاختيار")
        self.detail.setToolTip(str(path) if path else "")
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

    def set_theme(self, theme: str) -> None:
        self.icon_label.setPixmap(
            icon(self.icon_label.property("icon_name"), theme=theme, size=28, role="gold").pixmap(28, 28)
        )
