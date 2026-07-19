"""النافذة الرئيسية العربية لتطبيق نسخ الصور."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QThread
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from models.result_models import (
    ColumnInfo,
    DuplicatePolicy,
    JobResult,
    MultipleMatchPolicy,
    ProcessingSettings,
    ProcessingStats,
)
from services.excel_service import ExcelService
from services.report_service import ReportService
from ui.summary_dialog import SummaryDialog, open_path
from utils.constants import (
    APP_NAME,
    COPY_STATUS_AR,
    DUPLICATE_POLICY_AR,
    MATCH_STATUS_AR,
    MULTIPLE_POLICY_AR,
)
from workers.copy_worker import CopyWorker


class MainWindow(QMainWindow):
    """يدير اختيار المدخلات والمهام الخلفية وعرض النتائج."""

    MAX_VISIBLE_ROWS = 5000

    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = project_root
        self.settings = QSettings()
        self.excel_service = ExcelService()
        self.excel_path: Path | None = None
        self.source_path: Path | None = None
        self.destination_path: Path | None = None
        self.current_result: JobResult | None = None
        self.worker: CopyWorker | None = None
        self.worker_thread: QThread | None = None
        self.processing = False
        self._build_ui()
        self._restore_settings()
        self._update_controls()

    def _build_ui(self) -> None:
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1050, 720)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        central = QWidget(objectName="centralWidget")
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(18, 14, 18, 14)

        title = QLabel(APP_NAME, objectName="title")
        description = QLabel(
            "اختيار ملف Excel ومجلد الصور، ثم نسخ الصور المطابقة إلى مجلد جديد.", objectName="description"
        )
        outer.addWidget(title)
        outer.addWidget(description)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_setup_tab(), "الإعداد والمعالجة")
        self.tabs.addTab(self._build_results_tab(), "النتائج التفصيلية")
        outer.addWidget(self.tabs, 1)
        self.statusBar().showMessage("جاهز")

    @staticmethod
    def _card(title_text: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame(objectName="card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 16)
        layout.setSpacing(10)
        title = QLabel(title_text, objectName="sectionTitle")
        layout.addWidget(title)
        return card, layout

    @staticmethod
    def _path_row(button_text: str) -> tuple[QHBoxLayout, QLineEdit, QPushButton]:
        row = QHBoxLayout()
        field = QLineEdit()
        field.setReadOnly(True)
        field.setPlaceholderText("لم يتم الاختيار")
        button = QPushButton(button_text)
        row.addWidget(field, 1)
        row.addWidget(button)
        return row, field, button

    def _build_setup_tab(self) -> QWidget:
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 10, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)

        input_card, input_layout = self._card("ملف Excel والبيانات")
        excel_row, self.excel_field, self.excel_button = self._path_row("اختيار ملف Excel")
        self.excel_button.clicked.connect(self._select_excel)
        self.excel_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        input_layout.addLayout(excel_row)
        selections = QGridLayout()
        selections.addWidget(QLabel("ورقة العمل"), 0, 0)
        self.sheet_combo = QComboBox()
        self.sheet_combo.currentTextChanged.connect(self._sheet_changed)
        selections.addWidget(self.sheet_combo, 1, 0)
        selections.addWidget(QLabel("العمود"), 0, 1)
        self.column_combo = QComboBox()
        self.column_combo.currentIndexChanged.connect(self._update_controls)
        selections.addWidget(self.column_combo, 1, 1)
        input_layout.addLayout(selections)
        self.column_notice = QLabel("", objectName="muted")
        self.column_notice.setWordWrap(True)
        input_layout.addWidget(self.column_notice)
        layout.addWidget(input_card)

        folders_card, folders_layout = self._card("مجلدات الصور والحفظ")
        source_row, self.source_field, self.source_button = self._path_row("اختيار مجلد الصور")
        self.source_button.clicked.connect(self._select_source)
        self.source_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        folders_layout.addLayout(source_row)
        self.recursive_check = QCheckBox("البحث داخل المجلدات الفرعية")
        self.recursive_check.toggled.connect(self._update_controls)
        folders_layout.addWidget(self.recursive_check)
        destination_row, self.destination_field, self.destination_button = self._path_row("اختيار مجلد الحفظ")
        self.destination_button.clicked.connect(self._select_destination)
        self.destination_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        self.open_destination_button = QPushButton("فتح مجلد الحفظ")
        self.open_destination_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.open_destination_button.clicked.connect(self._open_destination)
        destination_row.addWidget(self.open_destination_button)
        folders_layout.addLayout(destination_row)
        layout.addWidget(folders_card)

        options_card, options_layout = self._card("خيارات المعالجة")
        options_grid = QGridLayout()
        self.case_check = QCheckBox("مطابقة أسماء الملفات دون حساسية لحالة الأحرف")
        self.case_check.setChecked(True)
        self.trim_check = QCheckBox("تجاهل المسافات المحيطة بالأرقام")
        self.trim_check.setChecked(True)
        self.ignore_duplicates_check = QCheckBox("تجاهل القيم المكررة في ملف Excel")
        self.ignore_duplicates_check.setChecked(True)
        self.preserve_name_check = QCheckBox("الحفاظ على اسم الصورة وامتدادها الأصليين")
        self.preserve_name_check.setChecked(True)
        self.preserve_name_check.setEnabled(False)
        self.preserve_name_check.setToolTip(
            "يحافظ التطبيق دائماً على الاسم والامتداد، إلا عند إنشاء اسم جديد لحل تعارض."
        )
        self.report_check = QCheckBox("إنشاء تقرير Excel بالنتائج")
        self.report_check.setChecked(True)
        self.open_after_check = QCheckBox("فتح مجلد النتائج بعد الانتهاء")
        options_grid.addWidget(self.case_check, 0, 0)
        options_grid.addWidget(self.trim_check, 0, 1)
        options_grid.addWidget(self.ignore_duplicates_check, 1, 0)
        options_grid.addWidget(self.report_check, 1, 1)
        options_grid.addWidget(self.preserve_name_check, 2, 0)
        options_grid.addWidget(self.open_after_check, 2, 1)
        options_grid.addWidget(QLabel("سياسة الملف الموجود في الوجهة"), 3, 0)
        self.duplicate_combo = QComboBox()
        for value, text in DUPLICATE_POLICY_AR.items():
            self.duplicate_combo.addItem(text, value)
        options_grid.addWidget(self.duplicate_combo, 4, 0)
        options_grid.addWidget(QLabel("عند وجود عدة صور مطابقة"), 3, 1)
        self.multiple_combo = QComboBox()
        for value, text in MULTIPLE_POLICY_AR.items():
            self.multiple_combo.addItem(text, value)
        options_grid.addWidget(self.multiple_combo, 4, 1)
        options_layout.addLayout(options_grid)
        layout.addWidget(options_card)

        progress_card, progress_layout = self._card("التقدم")
        self.stage_label = QLabel("جاهز")
        self.current_item_label = QLabel("", objectName="muted")
        self.current_item_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_details = QLabel("المعالج: 0 / 0 — 0% — الزمن: 0.00 ثانية")
        self.live_counters = QLabel("المنسوخ: 0 | غير الموجود: 0 | المتخطى: 0 | الفاشل: 0")
        progress_layout.addWidget(self.stage_label)
        progress_layout.addWidget(self.current_item_label)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_details)
        progress_layout.addWidget(self.live_counters)
        layout.addWidget(progress_card)

        buttons = QHBoxLayout()
        self.preview_button = QPushButton("معاينة المطابقة")
        self.preview_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        self.preview_button.clicked.connect(lambda: self._start_job(True))
        self.start_button = QPushButton("بدء المطابقة والنسخ", objectName="primary")
        self.start_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.start_button.clicked.connect(lambda: self._start_job(False))
        self.cancel_button = QPushButton("إلغاء العملية", objectName="danger")
        self.cancel_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserStop))
        self.cancel_button.clicked.connect(self._cancel_job)
        self.clear_button = QPushButton("مسح الاختيارات")
        self.clear_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        self.clear_button.clicked.connect(self._clear_selections)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.preview_button)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.clear_button)
        layout.addLayout(buttons)
        layout.addStretch()
        scroll.setWidget(content)
        tab_layout.addWidget(scroll)
        return tab

    def _build_results_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 10, 0, 0)
        stats_row = QHBoxLayout()
        self.stat_labels: dict[str, QLabel] = {}
        for key, title in [
            ("valid", "المعرّفات الصالحة"),
            ("scanned", "الصور المفهرسة"),
            ("matched", "المطابقة"),
            ("missing", "غير الموجودة"),
            ("multiple", "متعددة التطابق"),
        ]:
            card = QFrame(objectName="card")
            card_layout = QVBoxLayout(card)
            label = QLabel(title, objectName="muted")
            value = QLabel("0", objectName="statValue")
            card_layout.addWidget(label)
            card_layout.addWidget(value)
            stats_row.addWidget(card)
            self.stat_labels[key] = value
        layout.addLayout(stats_row)

        filters = QHBoxLayout()
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("بحث في النتائج...")
        self.search_field.textChanged.connect(self._filter_results)
        self.status_filter = QComboBox()
        self.status_filter.addItem("جميع الحالات", "")
        for value, text in MATCH_STATUS_AR.items():
            self.status_filter.addItem(text, value)
        self.status_filter.currentIndexChanged.connect(self._filter_results)
        self.export_button = QPushButton("تصدير النتائج")
        self.export_button.clicked.connect(self._export_results)
        filters.addWidget(self.search_field, 1)
        filters.addWidget(self.status_filter)
        filters.addWidget(self.export_button)
        layout.addLayout(filters)

        headers = [
            "التسلسل",
            "صف Excel",
            "القيمة الأصلية",
            "الرقم المعالج",
            "حالة المطابقة",
            "اسم الصورة",
            "مسار المصدر",
            "مسار الوجهة",
            "حالة النسخ",
            "ملاحظات",
        ]
        self.results_table = QTableWidget(0, len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        self.results_table.setSortingEnabled(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.results_table, 1)
        self.visible_notice = QLabel("", objectName="muted")
        layout.addWidget(self.visible_notice)

        actions = QHBoxLayout()
        copy_id = QPushButton("نسخ الرقم المحدد")
        copy_id.clicked.connect(self._copy_selected_identifier)
        open_source = QPushButton("فتح موقع ملف المصدر")
        open_source.clicked.connect(lambda: self._open_selected_path(6))
        open_destination = QPushButton("فتح موقع ملف الوجهة")
        open_destination.clicked.connect(lambda: self._open_selected_path(7))
        actions.addWidget(copy_id)
        actions.addWidget(open_source)
        actions.addWidget(open_destination)
        actions.addStretch()
        layout.addLayout(actions)
        return tab

    def _select_excel(self) -> None:
        initial = self.settings.value("last_excel_folder", str(Path.home()))
        filename, _ = QFileDialog.getOpenFileName(self, "اختيار ملف Excel", initial, "ملفات Excel (*.xlsx *.xlsm)")
        if not filename:
            return
        path = Path(filename)
        try:
            info = self.excel_service.workbook_info(path)
        except Exception as exc:
            QMessageBox.warning(self, "تعذر فتح الملف", str(exc))
            return
        self.excel_path = path
        self.excel_field.setText(str(path))
        self.excel_field.setToolTip(str(path))
        self.sheet_combo.blockSignals(True)
        self.sheet_combo.clear()
        self.sheet_combo.addItems(info.worksheets)
        preferred = self.settings.value("last_worksheet", info.active_worksheet)
        index = self.sheet_combo.findText(preferred)
        self.sheet_combo.setCurrentText(preferred if index >= 0 else info.active_worksheet)
        self.sheet_combo.blockSignals(False)
        self.settings.setValue("last_excel_folder", str(path.parent))
        self._load_columns()

    def _sheet_changed(self) -> None:
        if self.excel_path and self.sheet_combo.currentText():
            self._load_columns()

    def _load_columns(self) -> None:
        if not self.excel_path:
            return
        try:
            columns = self.excel_service.columns(self.excel_path, self.sheet_combo.currentText())
        except Exception as exc:
            QMessageBox.warning(self, "تعذر قراءة الأعمدة", str(exc))
            return
        self.column_combo.blockSignals(True)
        self.column_combo.clear()
        for column in columns:
            self.column_combo.addItem(column.display_name, column)
        required = self.excel_service.find_required_column(columns)
        if required:
            for index in range(self.column_combo.count()):
                item = self.column_combo.itemData(index)
                if isinstance(item, ColumnInfo) and item.index == required.index:
                    self.column_combo.setCurrentIndex(index)
                    break
            self.column_notice.setText("تم العثور على عمود «الرقم الذاتي» واختياره تلقائياً.")
            self.column_notice.setStyleSheet("color: #166534;")
        else:
            preferred = self.settings.value("last_column", "")
            preferred_index = self.column_combo.findText(preferred)
            if preferred_index >= 0:
                self.column_combo.setCurrentIndex(preferred_index)
            self.column_notice.setText("لم يُعثر على عمود «الرقم الذاتي». اختر العمود الصحيح يدوياً.")
            self.column_notice.setStyleSheet("color: #9A6700;")
        self.column_combo.blockSignals(False)
        self._update_controls()

    def _select_source(self) -> None:
        initial = self.settings.value("last_source_folder", str(Path.home()))
        folder = QFileDialog.getExistingDirectory(self, "اختيار مجلد الصور", initial)
        if folder:
            self.source_path = Path(folder)
            self.source_field.setText(folder)
            self.source_field.setToolTip(folder)
            self.settings.setValue("last_source_folder", folder)
            self._update_controls()

    def _select_destination(self) -> None:
        initial = self.settings.value("last_destination_folder", str(Path.home()))
        folder = QFileDialog.getExistingDirectory(self, "اختيار مجلد الحفظ", initial)
        if folder:
            candidate = Path(folder)
            if self.source_path and candidate.resolve() == self.source_path.resolve():
                QMessageBox.warning(self, "مجلد غير صالح", "يجب أن يختلف مجلد الحفظ عن مجلد الصور.")
                return
            self.destination_path = candidate
            self.destination_field.setText(folder)
            self.destination_field.setToolTip(folder)
            self.settings.setValue("last_destination_folder", folder)
            self._update_controls()

    def _valid_inputs(self) -> bool:
        column = self.column_combo.currentData()
        return bool(
            self.excel_path
            and self.excel_path.is_file()
            and self.sheet_combo.currentText()
            and isinstance(column, ColumnInfo)
            and self.source_path
            and self.source_path.is_dir()
            and self.destination_path
            and (not self.source_path or self.destination_path.resolve() != self.source_path.resolve())
        )

    def _update_controls(self) -> None:
        valid = self._valid_inputs()
        self.start_button.setEnabled(valid and not self.processing)
        self.preview_button.setEnabled(valid and not self.processing)
        self.cancel_button.setEnabled(self.processing)
        self.clear_button.setEnabled(not self.processing)
        self.open_destination_button.setEnabled(bool(self.destination_path and self.destination_path.exists()))
        for widget in (
            self.excel_button,
            self.source_button,
            self.destination_button,
            self.sheet_combo,
            self.column_combo,
        ):
            widget.setEnabled(not self.processing)

    def _processing_settings(self) -> ProcessingSettings:
        if not self._valid_inputs():
            raise ValueError("يرجى إكمال جميع الاختيارات المطلوبة.")
        return ProcessingSettings(
            excel_path=self.excel_path,
            worksheet=self.sheet_combo.currentText(),
            column=self.column_combo.currentData(),
            source_folder=self.source_path,
            destination_folder=self.destination_path,
            recursive=self.recursive_check.isChecked(),
            case_insensitive=self.case_check.isChecked(),
            trim_identifiers=self.trim_check.isChecked(),
            duplicate_policy=DuplicatePolicy(self.duplicate_combo.currentData()),
            multiple_match_policy=MultipleMatchPolicy(self.multiple_combo.currentData()),
            generate_report=self.report_check.isChecked(),
            open_destination_after=self.open_after_check.isChecked(),
            ignore_duplicate_identifiers=self.ignore_duplicates_check.isChecked(),
        )

    def _start_job(self, preview_only: bool) -> None:
        try:
            settings = self._processing_settings()
        except ValueError as exc:
            QMessageBox.warning(self, "بيانات ناقصة", str(exc))
            return
        if not preview_only:
            settings.destination_folder.mkdir(parents=True, exist_ok=True)
        self._save_settings()
        self.processing = True
        self.progress_bar.setRange(0, 0)
        self.stage_label.setText("بدء المعالجة...")
        self.current_item_label.clear()
        self.statusBar().showMessage("المعالجة جارية")
        self._update_controls()
        self.worker_thread = QThread(self)
        self.worker = CopyWorker(settings, preview_only, self.project_root / "logs")
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_progress)
        self.worker.completed.connect(lambda result: self._on_completed(result, preview_only))
        self.worker.cancelled.connect(self._on_cancelled)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self._thread_finished)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def _cancel_job(self) -> None:
        if self.worker:
            self.worker.cancel()
            self.cancel_button.setEnabled(False)
            self.stage_label.setText("جارٍ إلغاء العملية بأمان...")

    def _on_progress(self, stage: str, current: int, total: int, item: str, stats: ProcessingStats) -> None:
        self.stage_label.setText(stage)
        self.current_item_label.setText(item)
        if total > 0:
            percentage = min(100, round(current * 100 / total))
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(percentage)
        else:
            percentage = 0
            self.progress_bar.setRange(0, 0)
        self.progress_details.setText(
            f"المعالج: {current} / {total or '—'} — {percentage}% — الزمن: {stats.elapsed_seconds:.2f} ثانية"
        )
        self.live_counters.setText(
            f"المنسوخ: {stats.copied_files} | غير الموجود: {stats.unmatched_identifiers} | "
            f"المتخطى: {stats.skipped_files} | الفاشل: {stats.failed_copies}"
        )

    def _on_completed(self, result: JobResult, preview_only: bool) -> None:
        self.current_result = result
        self._populate_results(result)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.statusBar().showMessage("اكتملت المعاينة" if preview_only else "اكتملت العملية")
        self.tabs.setCurrentIndex(1)
        if preview_only:
            QMessageBox.information(
                self,
                "اكتملت المعاينة",
                f"المعرّفات الصالحة: {result.stats.valid_identifiers}\n"
                f"المطابقة: {result.stats.matched_identifiers}\n"
                f"غير الموجودة: {result.stats.unmatched_identifiers}\n"
                f"التطابقات المتعددة: {result.stats.multiple_match_identifiers}",
            )
        else:
            dialog = SummaryDialog(result, self)
            if dialog.exec() == 2:
                index = self.status_filter.findData("not_found")
                self.status_filter.setCurrentIndex(index)
            if result.settings.open_destination_after:
                open_path(result.settings.destination_folder)

    def _on_cancelled(self, result: JobResult) -> None:
        self.current_result = result
        self._populate_results(result)
        QMessageBox.information(self, "تم الإلغاء", "توقفت العملية بأمان. بقيت الملفات التي اكتمل نسخها.")
        self.statusBar().showMessage("تم إلغاء العملية")

    def _on_failed(self, message: str, log_path: str) -> None:
        QMessageBox.critical(self, "تعذر إكمال العملية", f"{message}\n\nملف السجل:\n{log_path}")
        self.statusBar().showMessage("فشلت العملية")

    def _thread_finished(self) -> None:
        self.processing = False
        self.worker = None
        self.worker_thread = None
        self._update_controls()

    def _populate_results(self, result: JobResult) -> None:
        self.results_table.setSortingEnabled(False)
        self.results_table.setRowCount(0)
        records = result.records[: self.MAX_VISIBLE_ROWS]
        for row, record in enumerate(records):
            self.results_table.insertRow(row)
            values = [
                str(record.sequence),
                str(record.excel_row),
                record.original_value,
                record.identifier,
                MATCH_STATUS_AR[record.match_status.value],
                record.source_filename,
                str(record.source_path or ""),
                str(record.destination_path or ""),
                COPY_STATUS_AR[record.copy_status.value],
                record.notes,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, record.match_status.value)
                if column in (0, 1):
                    item.setData(Qt.ItemDataRole.DisplayRole, int(value))
                self.results_table.setItem(row, column, item)
        self.results_table.setSortingEnabled(True)
        hidden = max(0, len(result.records) - len(records))
        self.visible_notice.setText(
            f"يُعرض أول {len(records)} سجل من أصل {len(result.records)}. التقرير يتضمن جميع النتائج."
            if hidden
            else f"عدد النتائج: {len(records)}"
        )
        self.stat_labels["valid"].setText(str(result.stats.valid_identifiers))
        self.stat_labels["scanned"].setText(str(result.stats.source_images_scanned))
        self.stat_labels["matched"].setText(str(result.stats.matched_identifiers))
        self.stat_labels["missing"].setText(str(result.stats.unmatched_identifiers))
        self.stat_labels["multiple"].setText(str(result.stats.multiple_match_identifiers))
        self._filter_results()

    def _filter_results(self) -> None:
        search = self.search_field.text().strip().casefold()
        status = self.status_filter.currentData()
        for row in range(self.results_table.rowCount()):
            values = [self.results_table.item(row, column).text() for column in range(self.results_table.columnCount())]
            row_status = self.results_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            visible = (not search or any(search in value.casefold() for value in values)) and (
                not status or row_status == status
            )
            self.results_table.setRowHidden(row, not visible)

    def _export_results(self) -> None:
        if not self.current_result:
            QMessageBox.information(self, "لا توجد نتائج", "نفّذ المعاينة أو النسخ أولاً.")
            return
        try:
            path = ReportService().create(self.current_result)
            self.current_result.report_path = path
            QMessageBox.information(self, "تم التصدير", f"تم إنشاء التقرير:\n{path}")
        except Exception as exc:
            QMessageBox.warning(self, "تعذر التصدير", f"تعذر إنشاء التقرير: {exc}")

    def _copy_selected_identifier(self) -> None:
        row = self.results_table.currentRow()
        if row < 0:
            return
        QApplication.clipboard().setText(self.results_table.item(row, 3).text())
        self.statusBar().showMessage("تم نسخ الرقم المحدد", 3000)

    def _open_selected_path(self, column: int) -> None:
        row = self.results_table.currentRow()
        if row < 0:
            return
        value = self.results_table.item(row, column).text()
        path = Path(value) if value else None
        folder = path.parent if path and path.is_file() else None
        if not folder or not folder.exists():
            QMessageBox.warning(self, "المسار غير متاح", "الملف المحدد لم يعد موجوداً أو لا يمكن الوصول إليه.")
            return
        open_path(folder)

    def _open_destination(self) -> None:
        if self.destination_path:
            open_path(self.destination_path)

    def _clear_selections(self) -> None:
        self.excel_path = self.source_path = self.destination_path = None
        for field in (self.excel_field, self.source_field, self.destination_field):
            field.clear()
        self.sheet_combo.clear()
        self.column_combo.clear()
        self.column_notice.clear()
        self.current_result = None
        self.results_table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.stage_label.setText("جاهز")
        self.current_item_label.clear()
        self._update_controls()

    def _restore_settings(self) -> None:
        geometry = self.settings.value("window_geometry")
        if geometry:
            self.restoreGeometry(geometry)
        self.recursive_check.setChecked(self.settings.value("recursive", False, type=bool))
        self.report_check.setChecked(self.settings.value("generate_report", True, type=bool))
        duplicate = self.settings.value("duplicate_policy", DuplicatePolicy.SKIP.value)
        index = self.duplicate_combo.findData(duplicate)
        self.duplicate_combo.setCurrentIndex(max(0, index))
        last_excel = self.settings.value("last_excel_file", "")
        if last_excel and Path(last_excel).is_file():
            self.excel_path = Path(last_excel)
            self.excel_field.setText(last_excel)
            try:
                info = self.excel_service.workbook_info(self.excel_path)
                self.sheet_combo.addItems(info.worksheets)
                preferred = self.settings.value("last_worksheet", info.active_worksheet)
                self.sheet_combo.setCurrentText(preferred if preferred in info.worksheets else info.active_worksheet)
                self._load_columns()
            except Exception:
                self.excel_path = None
                self.excel_field.clear()
        last_source = self.settings.value("last_source_folder", "")
        if last_source and Path(last_source).is_dir():
            self.source_path = Path(last_source)
            self.source_field.setText(last_source)
        last_destination = self.settings.value("last_destination_folder", "")
        if last_destination and Path(last_destination).is_dir():
            self.destination_path = Path(last_destination)
            self.destination_field.setText(last_destination)

    def _save_settings(self) -> None:
        self.settings.setValue("window_geometry", self.saveGeometry())
        if self.excel_path:
            self.settings.setValue("last_excel_file", str(self.excel_path))
        self.settings.setValue("last_worksheet", self.sheet_combo.currentText())
        self.settings.setValue("last_column", self.column_combo.currentText())
        self.settings.setValue("recursive", self.recursive_check.isChecked())
        self.settings.setValue("duplicate_policy", self.duplicate_combo.currentData())
        self.settings.setValue("generate_report", self.report_check.isChecked())

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.processing:
            answer = QMessageBox.question(
                self,
                "عملية قيد التنفيذ",
                "توجد عملية قيد التنفيذ. هل تريد إلغاءها وانتظار توقفها قبل الإغلاق؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            if self.worker:
                self.worker.cancel()
            if self.worker_thread and not self.worker_thread.wait(5000):
                QMessageBox.warning(self, "انتظار الإلغاء", "لم تتوقف العملية بعد. حاول الإغلاق مرة أخرى بعد لحظات.")
                event.ignore()
                return
        self._save_settings()
        event.accept()
