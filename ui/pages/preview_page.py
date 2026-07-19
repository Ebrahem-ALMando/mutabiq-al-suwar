"""معاينة model/view مع تحرير يدوي ومعرض كسول."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QImageReader, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QSlider,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from models.result_models import JobResult, MatchStatus
from ui.models.result_model import ResultFilterProxy, ResultTableModel
from utils.constants import MATCH_STATUS_AR


class PreviewPage(QWidget):
    recordsChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.result: JobResult | None = None
        self.model = ResultTableModel()
        self.proxy = ResultFilterProxy()
        self.proxy.setSourceModel(self.model)
        layout = QVBoxLayout(self)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("بحث بالمعرّف أو الاسم أو المسار...")
        self.search.textChanged.connect(self.proxy.set_search)
        self.status = QComboBox()
        self.status.addItem("جميع الحالات", "")
        for value, text in MATCH_STATUS_AR.items():
            self.status.addItem(text, value)
        self.status.currentIndexChanged.connect(lambda: self.proxy.set_status(self.status.currentData()))
        self.summary = QLabel("لا توجد معاينة", objectName="muted")
        filters.addWidget(self.search, 1)
        filters.addWidget(self.status)
        filters.addWidget(self.summary)
        layout.addLayout(filters)
        self.tabs = QTabWidget()
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.tabs.addTab(self.table, "عرض الجدول")
        gallery_page = QWidget()
        gallery_layout = QVBoxLayout(gallery_page)
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("حجم الصور المصغرة"))
        self.thumbnail_size = QSlider(Qt.Orientation.Horizontal)
        self.thumbnail_size.setRange(96, 240)
        self.thumbnail_size.setValue(144)
        self.thumbnail_size.valueChanged.connect(self._refresh_gallery)
        size_row.addWidget(self.thumbnail_size)
        gallery_layout.addLayout(size_row)
        self.gallery = QListWidget()
        self.gallery.setViewMode(QListWidget.ViewMode.IconMode)
        self.gallery.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.gallery.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        gallery_layout.addWidget(self.gallery)
        self.tabs.addTab(gallery_page, "المعرض")
        layout.addWidget(self.tabs)

    def set_result(self, result: JobResult) -> None:
        self.result = result
        self.model.set_records(result.records)
        self.summary.setText(
            f"{len(result.records):,} نتيجة | مطابق {result.stats.matched_identifiers:,} | غير موجود {result.stats.unmatched_identifiers:,}"
        )
        self._refresh_gallery()

    def _source_row(self) -> int:
        indexes = self.table.selectionModel().selectedRows()
        return self.proxy.mapToSource(indexes[0]).row() if indexes else -1

    def _context_menu(self, position) -> None:
        row = self._source_row()
        record = self.model.record(row)
        if not record:
            return
        menu = QMenu(self)
        exclude = menu.addAction("استبعاد من النسخ" if record.selected_for_copy else "إعادة التضمين")
        review = menu.addAction("وضع علامة تمت المراجعة")
        choose = menu.addAction("اختيار صورة محلية أخرى")
        destination = menu.addAction("تعديل اسم الوجهة")
        note = menu.addAction("إضافة ملاحظة")
        restore = menu.addAction("استعادة القرار التلقائي")
        action = menu.exec(self.table.viewport().mapToGlobal(position))
        if action == exclude:
            record.selected_for_copy = not record.selected_for_copy
            record.manually_modified = True
        elif action == review:
            record.reviewed = True
            record.manually_modified = True
        elif action == choose:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "اختيار صورة",
                str(record.source_path.parent if record.source_path else Path.home()),
                "الصور (*.jpg *.jpeg *.png *.webp *.bmp *.gif *.tif *.tiff *.heic *.jfif)",
            )
            if filename:
                record.source_path = Path(filename)
                record.match_status = MatchStatus.MANUAL
                record.selected_for_copy = True
                record.manually_modified = True
        elif action == destination:
            value, accepted = QInputDialog.getText(
                self,
                "اسم الوجهة",
                "الاسم الجديد مع الامتداد:",
                text=record.destination_filename_override or record.source_filename,
            )
            if accepted and value.strip():
                record.destination_filename_override = value.strip()
                record.manually_modified = True
        elif action == note:
            value, accepted = QInputDialog.getMultiLineText(self, "ملاحظة", "الملاحظة:", record.notes)
            if accepted:
                record.notes = value
                record.manually_modified = True
        elif action == restore:
            record.selected_for_copy = True
            record.destination_filename_override = ""
            record.manually_modified = False
            record.reviewed = False
        else:
            return
        self.model.notify_record_changed(row)
        self.recordsChanged.emit()
        self._refresh_gallery()

    def _refresh_gallery(self) -> None:
        self.gallery.clear()
        if not self.result:
            return
        size = self.thumbnail_size.value()
        self.gallery.setIconSize(QSize(size, size))
        for record in self.result.records[:1000]:
            if not record.source_path:
                continue
            item = QListWidgetItem(
                f"{record.identifier}\n{record.source_filename}\n{MATCH_STATUS_AR[record.match_status.value]}"
            )
            reader = QImageReader(str(record.source_path))
            reader.setAutoTransform(True)
            reader.setScaledSize(QSize(size, size))
            pixmap = QPixmap.fromImage(reader.read())
            if not pixmap.isNull():
                item.setIcon(QIcon(pixmap))
            item.setToolTip(str(record.source_path))
            self.gallery.addItem(item)
