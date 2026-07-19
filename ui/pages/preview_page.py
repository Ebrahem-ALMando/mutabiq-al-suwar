"""معاينة model/view مع تحرير يدوي ومعرض كسول."""

from __future__ import annotations

import csv
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QImageReader, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSlider,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from models.result_models import JobResult, MatchStatus
from ui.components.controls import EmptyState, SegmentedControl
from ui.icons import icon
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
        self.settings = QSettings()
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
        self.clear_filters = QPushButton("مسح المرشحات")
        self.clear_filters.clicked.connect(self._clear_filters)
        self.columns_button = QPushButton("الأعمدة")
        self.columns_button.clicked.connect(self._columns_menu)
        self.export_button = QPushButton("تصدير النتائج")
        self.export_button.clicked.connect(self._export_visible)
        self.density = QComboBox()
        self.density.addItem("مريح", 46)
        self.density.addItem("متوسط", 40)
        self.density.addItem("مضغوط", 34)
        self.density.currentIndexChanged.connect(self._apply_density)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.status)
        filters.addWidget(self.clear_filters)
        filters.addWidget(self.columns_button)
        filters.addWidget(self.export_button)
        filters.addWidget(self.density)
        filters.addWidget(self.summary)
        layout.addLayout(filters)
        self.view_switch = SegmentedControl([("الجدول", "table"), ("المعرض", "images")])
        self.view_switch.changed.connect(lambda index: self.tabs.setCurrentIndex(index))
        layout.addWidget(self.view_switch, 0, Qt.AlignmentFlag.AlignRight)
        self.tabs = QTabWidget()
        self.tabs.tabBar().hide()
        self.table = QTableView()
        self.table.setObjectName("resultsTable")
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(72)
        header.setSectionsMovable(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.model.columnCount() - 1, QHeaderView.ResizeMode.Stretch)
        header.sectionResized.connect(self._save_widths)
        self._restore_widths()
        self.empty = EmptyState(
            "لا توجد نتائج للعرض",
            "ابدأ معاينة من المعالج، أو غيّر مرشحات البحث.",
            icon_name="inbox",
            parent=self.table.viewport(),
        )
        self.empty.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.empty.show()
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
        self.tabs.currentChanged.connect(self.view_switch.set_index)
        layout.addWidget(self.tabs)
        self.set_theme("light")

    def set_result(self, result: JobResult) -> None:
        self.result = result
        self.model.set_records(result.records)
        self.summary.setText(
            f"{len(result.records):,} نتيجة | مطابق {result.stats.matched_identifiers:,} | غير موجود {result.stats.unmatched_identifiers:,}"
        )
        self.empty.setVisible(not bool(result.records))
        self._position_empty()
        self._refresh_gallery()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_empty()

    def _position_empty(self) -> None:
        if hasattr(self, "empty"):
            self.empty.setGeometry(self.table.viewport().rect())

    def _clear_filters(self) -> None:
        self.search.clear()
        self.status.setCurrentIndex(0)

    def _apply_density(self) -> None:
        self.table.verticalHeader().setDefaultSectionSize(int(self.density.currentData() or 42))

    def _save_widths(self, *_args) -> None:
        header = self.table.horizontalHeader()
        self.settings.setValue(
            "preview_column_widths", [header.sectionSize(i) for i in range(self.model.columnCount())]
        )

    def _restore_widths(self) -> None:
        widths = self.settings.value("preview_column_widths", [])
        if isinstance(widths, list) and len(widths) == self.model.columnCount():
            for index, width in enumerate(widths):
                self.table.setColumnWidth(index, max(72, int(width)))
        else:
            defaults = [88, 120, 130, 132, 82, 98, 220, 190, 120, 180]
            for index, width in enumerate(defaults):
                self.table.setColumnWidth(index, width)

    def _columns_menu(self) -> None:
        menu = QMenu(self)
        for index, heading in enumerate(self.model.HEADERS):
            action = menu.addAction(heading)
            action.setCheckable(True)
            action.setChecked(not self.table.isColumnHidden(index))
            action.toggled.connect(lambda visible, column=index: self.table.setColumnHidden(column, not visible))
        menu.popup(self.columns_button.mapToGlobal(self.columns_button.rect().bottomLeft()))

    def _export_visible(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(self, "تصدير النتائج الظاهرة", "results.csv", "CSV (*.csv)")
        if not filename:
            return
        with open(filename, "w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(self.model.HEADERS)
            for row in range(self.proxy.rowCount()):
                writer.writerow([self.proxy.index(row, column).data() for column in range(self.proxy.columnCount())])

    def set_theme(self, theme: str) -> None:
        self.view_switch.set_theme(theme)
        self.clear_filters.setIcon(icon("search", theme=theme))
        self.columns_button.setIcon(icon("table", theme=theme))
        self.export_button.setIcon(icon("file-chart", theme=theme))
        self.empty.set_theme(theme)

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
