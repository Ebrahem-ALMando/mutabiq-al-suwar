"""صفحة تعريف وخصوصية ومعلومات نظام."""

from __future__ import annotations

import platform
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.summary_dialog import open_path
from utils.app_paths import AppPaths
from utils.constants import APP_NAME, APP_SECONDARY_NAME, PRIVACY_STATEMENT, SUPPORTED_IMAGE_EXTENSIONS
from utils.version import APP_VERSION, BUILD_NUMBER


class AboutPage(QWidget):
    def __init__(self, paths: AppPaths, project_root: Path, logo_path: Path) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        logo = QLabel()
        logo.setPixmap(QIcon(str(logo_path)).pixmap(112, 112))
        layout.addWidget(logo)
        layout.addWidget(QLabel(APP_NAME, objectName="pageTitle"))
        layout.addWidget(QLabel(APP_SECONDARY_NAME, objectName="sectionTitle"))
        layout.addWidget(QLabel(f"الإصدار {APP_VERSION} — البناء {BUILD_NUMBER}"))
        privacy = QLabel(PRIVACY_STATEMENT)
        privacy.setWordWrap(True)
        layout.addWidget(privacy)
        layout.addWidget(
            QLabel("الصيغ المدعومة: Excel وCSV وTSV؛ الصور: " + ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS)))
        )
        layout.addWidget(
            QLabel("يعتمد على Python وPySide6 وopenpyxl. لا توجد شركة أو جهة قانونية مصطنعة، ولا تحليلات أو تتبع.")
        )
        actions = QHBoxLayout()
        docs = QPushButton("فتح الدليل المحلي")
        docs.clicked.connect(lambda: open_path(project_root / "README.md"))
        data = QPushButton("فتح مجلد بيانات التطبيق")
        data.clicked.connect(lambda: open_path(paths.root))
        logs = QPushButton("فتح السجلات")
        logs.clicked.connect(lambda: open_path(paths.logs))
        system = QPushButton("نسخ معلومات النظام")
        system.clicked.connect(
            lambda: QApplication.clipboard().setText(
                f"{APP_NAME} {APP_VERSION}\n{platform.platform()}\nPython {platform.python_version()}"
            )
        )
        [actions.addWidget(button) for button in (docs, data, logs, system)]
        actions.addStretch()
        layout.addLayout(actions)
        layout.addStretch()
