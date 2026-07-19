"""مركز تقارير العمليات السابقة."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from repositories.history_repository import HistoryRepository
from ui.summary_dialog import open_path


class ReportsPage(QWidget):
    def __init__(self, history: HistoryRepository) -> None:
        super().__init__()
        self.history = history
        self.rows: list[dict] = []
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("التقارير والمنشورات المحلية", objectName="sectionTitle"))
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["التاريخ", "الدفعة", "Excel", "التقرير", "المنشور"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        actions = QHBoxLayout()
        open_report = QPushButton("فتح التقرير")
        open_report.clicked.connect(lambda: self._open("report_path"))
        open_manifest = QPushButton("فتح المنشور")
        open_manifest.clicked.connect(lambda: self._open("manifest_path"))
        refresh = QPushButton("تحديث")
        refresh.clicked.connect(self.refresh)
        actions.addWidget(open_report)
        actions.addWidget(open_manifest)
        actions.addWidget(refresh)
        actions.addStretch()
        layout.addLayout(actions)
        self.refresh()

    def refresh(self) -> None:
        self.rows = self.history.recent_batches(500)
        self.table.setRowCount(len(self.rows))
        for row, batch in enumerate(self.rows):
            for column, value in enumerate(
                (
                    batch["started_at"][:16].replace("T", " "),
                    batch["batch_id"][:8],
                    batch["excel_filename"],
                    batch["report_path"] or "—",
                    batch["manifest_path"] or "—",
                )
            ):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))

    def _open(self, key: str) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.rows) and self.rows[row][key]:
            open_path(Path(self.rows[row][key]))
