"""سجل العمليات مع فتح المنشور والتراجع الآمن."""

from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from repositories.history_repository import HistoryRepository
from services.undo_service import UndoService
from ui.dialogs import confirm_dialog, message_dialog
from ui.summary_dialog import open_path


class HistoryPage(QWidget):
    historyChanged = Signal()

    def __init__(self, history: HistoryRepository) -> None:
        super().__init__()
        self.history = history
        self.rows: list[dict] = []
        layout = QVBoxLayout(self)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("بحث بمعرّف الدفعة أو الملف أو المسار...")
        self.status = QComboBox()
        self.status.addItem("جميع الحالات", "")
        for key, text in [("success", "ناجحة"), ("partial", "جزئية"), ("cancelled", "ملغاة"), ("failure", "فاشلة")]:
            self.status.addItem(text, key)
        refresh = QPushButton("تحديث")
        refresh.clicked.connect(self.refresh)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.status)
        filters.addWidget(refresh)
        layout.addLayout(filters)
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(
            [
                "الدفعة",
                "التاريخ",
                "ملف البيانات",
                "المصدر",
                "الوجهة",
                "المعرّفات",
                "المطابق",
                "المنسوخ",
                "الحالة",
                "التراجع",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        actions = QHBoxLayout()
        for text, slot in [
            ("فتح الوجهة", self._open_destination),
            ("فتح التقرير", self._open_report),
            ("تصدير المنشور", self._export_manifest),
            ("تراجع آمن", self._undo),
            ("حذف سجل فقط", self._delete_record),
        ]:
            button = QPushButton(text)
            button.clicked.connect(slot)
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        self.search.textChanged.connect(self.refresh)
        self.status.currentIndexChanged.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        self.rows = self.history.recent_batches(500, self.search.text().strip(), self.status.currentData())
        self.table.setRowCount(len(self.rows))
        for row, batch in enumerate(self.rows):
            values = (
                batch["batch_id"][:8],
                batch["started_at"][:16].replace("T", " "),
                batch["excel_filename"],
                batch["source_folder"],
                batch["destination_folder"],
                batch["total_identifiers"],
                batch["matched_count"],
                batch["copied_count"],
                batch["status"],
                batch["undone_status"],
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))

    def selected(self) -> dict | None:
        row = self.table.currentRow()
        return self.rows[row] if 0 <= row < len(self.rows) else None

    def _open_destination(self) -> None:
        if batch := self.selected():
            open_path(Path(batch["destination_folder"]))

    def _open_report(self) -> None:
        if batch := self.selected():
            open_path(Path(batch["report_path"]))

    def _export_manifest(self) -> None:
        batch = self.selected()
        if not batch or not Path(batch["manifest_path"]).is_file():
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "تصدير المنشور", f"batch_{batch['batch_id']}.json", "JSON (*.json)"
        )
        if filename:
            shutil.copy2(batch["manifest_path"], filename)

    def _undo(self) -> None:
        batch = self.selected()
        if not batch or not batch["manifest_path"]:
            return
        try:
            manifest, candidates = UndoService(self.history).plan(Path(batch["manifest_path"]))
        except Exception as exc:
            message_dialog(self, "التراجع غير متاح", str(exc), severity="warning").exec()
            return
        safe = sum(item.safe for item in candidates)
        unsafe = len(candidates) - safe
        if not confirm_dialog(
            self,
            "تأكيد التراجع الآمن",
            f"سيُحذف {safe} ملفاً أنشأتها هذه الدفعة فقط. لن يُحذف {unsafe} ملفاً تغير أو لم يعد آمناً. هل تتابع؟",
            confirm_text="تراجع آمن",
            destructive=True,
        ):
            return
        result = UndoService(self.history).execute(Path(batch["manifest_path"]), True)
        message_dialog(
            self,
            "نتيجة التراجع",
            f"حُذف {len(result.removed)} ملفاً، وتُرك {len(result.skipped)} ملفاً.\n{result.report_path}",
            severity="success",
        ).exec()
        self.refresh()
        self.historyChanged.emit()

    def _delete_record(self) -> None:
        batch = self.selected()
        if not batch:
            return
        if not confirm_dialog(
            self,
            "حذف السجل",
            "سيُحذف سجل الدفعة فقط ولن تُحذف أي ملفات. هل تتابع؟",
            confirm_text="حذف السجل",
            destructive=True,
        ):
            return
        with self.history.connect() as connection:
            connection.execute("DELETE FROM batches WHERE batch_id=?", (batch["batch_id"],))
        self.refresh()
        self.historyChanged.emit()
