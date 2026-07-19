"""نافذة ملخص المعالجة النهائية."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from models.result_models import JobResult


def open_path(path: Path) -> bool:
    """افتح ملفاً أو مجلداً عبر تطبيق النظام الافتراضي."""

    return path.exists() and QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))


class SummaryDialog(QDialog):
    """يعرض الإحصاءات النهائية وروابط التقرير والوجهة."""

    def __init__(self, result: JobResult, parent=None) -> None:
        super().__init__(parent)
        self.result = result
        self.setWindowTitle("ملخص العملية")
        self.setMinimumSize(700, 520)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        outcome = {
            "success": ("اكتملت العملية بنجاح", "#166534"),
            "partial": ("اكتملت العملية مع ملاحظات", "#9A6700"),
            "failure": ("تعذر إكمال العملية", "#B42318"),
            "cancelled": ("تم إلغاء العملية", "#9A6700"),
        }[result.outcome]
        heading = QLabel(outcome[0])
        heading.setStyleSheet(f"font-size: 21px; font-weight: 700; color: {outcome[1]};")
        layout.addWidget(heading)
        if result.settings.dry_run:
            simulation = QLabel("محاكاة مكتملة: لم تُنسخ أي ملفات ولم تتغير ملفات المصدر أو الوجهة.")
            simulation.setObjectName("sectionTitle")
            simulation.setWordWrap(True)
            layout.addWidget(simulation)

        labels = [
            ("إجمالي صفوف Excel", result.stats.total_excel_rows),
            ("القيم الفارغة", result.stats.empty_values),
            ("المعرّفات الصالحة", result.stats.valid_identifiers),
            ("المعرّفات الفريدة", result.stats.unique_identifiers),
            ("القيم المكررة", result.stats.duplicate_identifiers),
            ("الصور المفهرسة", result.stats.source_images_scanned),
            ("المعرّفات المطابقة", result.stats.matched_identifiers),
            ("الملفات المنسوخة", result.stats.copied_files),
            ("الملفات المتخطاة", result.stats.skipped_files),
            ("الملفات المعاد تسميتها", result.stats.renamed_files),
            ("المعرّفات غير الموجودة", result.stats.unmatched_identifiers),
            ("التطابقات المتعددة", result.stats.multiple_match_identifiers),
            ("عمليات النسخ الفاشلة", result.stats.failed_copies),
            ("المدة الإجمالية", f"{result.stats.elapsed_seconds:.2f} ثانية"),
        ]
        grid = QGridLayout()
        for index, (name, value) in enumerate(labels):
            row, column = divmod(index, 2)
            text = QLabel(f"<b>{name}:</b> {value}")
            text.setTextFormat(Qt.TextFormat.RichText)
            grid.addWidget(text, row, column)
        layout.addLayout(grid)

        paths = QLabel(
            f"<b>مجلد النتائج:</b> {result.settings.destination_folder}<br>"
            f"<b>ملف التقرير:</b> {result.report_path or 'لم يُنشأ'}<br>"
            f"<b>ملف السجل:</b> {result.log_path or 'غير متاح'}"
            f"<br><b>منشور العملية:</b> {result.manifest_path or 'لم يُنشأ'}"
        )
        paths.setWordWrap(True)
        paths.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(paths)

        actions = QHBoxLayout()
        open_destination = QPushButton("فتح مجلد النتائج")
        open_destination.clicked.connect(lambda: open_path(result.settings.destination_folder))
        actions.addWidget(open_destination)
        open_report = QPushButton("فتح التقرير")
        open_report.setEnabled(bool(result.report_path and result.report_path.exists()))
        open_report.clicked.connect(lambda: result.report_path and open_path(result.report_path))
        actions.addWidget(open_report)
        show_missing = QPushButton("عرض الملفات غير الموجودة")
        show_missing.clicked.connect(lambda: self.done(2))
        actions.addWidget(show_missing)
        layout.addLayout(actions)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("إغلاق")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
