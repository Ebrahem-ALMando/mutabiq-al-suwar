"""معالج عملية من خمس خطوات يحتفظ بالحالة ولا ينسخ قبل المعاينة."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.operation_state import OperationState
from models.result_models import (
    ColumnInfo,
    DuplicatePolicy,
    JobResult,
    MatchingMode,
    MultipleMatchPolicy,
    NormalizationOptions,
    ProcessingSettings,
    TransformationRule,
)
from services.excel_service import ExcelService
from ui.components.drop_zone import DropZone
from ui.components.inputs import NumericDoubleSpinBox, NumericSpinBox
from ui.dialogs import message_dialog
from ui.icons import icon
from utils.constants import DUPLICATE_POLICY_AR, MULTIPLE_POLICY_AR, SUPPORTED_EXCEL_EXTENSIONS


class OperationPage(QWidget):
    previewRequested = Signal(object)
    executeRequested = Signal(object, object)
    cancelRequested = Signal()
    pauseRequested = Signal(bool)

    STEPS = ["ملف البيانات", "مصدر الصور", "قواعد المطابقة", "معاينة النتائج", "النسخ والتقرير"]

    def __init__(self) -> None:
        super().__init__()
        self.excel = ExcelService()
        self.excel_path: Path | None = None
        self.source_path: Path | None = None
        self.destination_path: Path | None = None
        self.preview_result: JobResult | None = None
        self.rules: list[TransformationRule] = []
        self.current_step = 0
        layout = QVBoxLayout(self)
        self.simulation_banner = QFrame(objectName="banner")
        banner_layout = QHBoxLayout(self.simulation_banner)
        banner_layout.addWidget(QLabel("محاكاة دون نسخ: ستُراجع المسارات والتعارضات ولن تُنسخ صور."))
        self.simulation_banner.hide()
        layout.addWidget(self.simulation_banner)
        stepper = QHBoxLayout()
        self.step_buttons: list[QPushButton] = []
        for index, title in enumerate(self.STEPS):
            button = QPushButton(f"{index + 1}  {title}")
            button.setObjectName("wizardStep")
            button.setProperty("step", index)
            button.clicked.connect(lambda checked=False, step=index: self.go_to(step))
            self.step_buttons.append(button)
            stepper.addWidget(button)
        layout.addLayout(stepper)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._data_step())
        self.stack.addWidget(self._folders_step())
        self.stack.addWidget(self._rules_step())
        self.stack.addWidget(self._preview_step())
        self.stack.addWidget(self._execute_step())
        layout.addWidget(self.stack, 1)
        self._wire_invalidation()
        nav = QHBoxLayout()
        self.back_button = QPushButton("السابق")
        self.back_button.clicked.connect(lambda: self.go_to(self.current_step - 1))
        self.next_button = QPushButton("التالي", objectName="primary")
        self.next_button.clicked.connect(self._next)
        nav.addWidget(self.back_button)
        nav.addStretch()
        nav.addWidget(self.next_button)
        layout.addLayout(nav)
        self.go_to(0)

    def _data_step(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("اختر ملف Excel أو CSV ثم راجع اكتشاف الأعمدة", objectName="sectionTitle"))
        self.excel_zone = DropZone("ملف البيانات", "file", SUPPORTED_EXCEL_EXTENSIONS)
        self.excel_zone.pathDropped.connect(self.set_excel_path)
        layout.addWidget(self.excel_zone)
        select = QPushButton("اختيار ملف بيانات")
        select.clicked.connect(self._choose_excel)
        layout.addWidget(select)
        grid = QGridLayout()
        grid.addWidget(QLabel("ورقة العمل"), 0, 0)
        self.sheet_combo = QComboBox()
        self.sheet_combo.currentTextChanged.connect(self._load_columns)
        grid.addWidget(self.sheet_combo, 1, 0)
        grid.addWidget(QLabel("عمود المعرّف"), 0, 1)
        self.column_combo = QComboBox()
        grid.addWidget(self.column_combo, 1, 1)
        grid.addWidget(QLabel("عمود الاسم الاختياري"), 0, 2)
        self.secondary_combo = QComboBox()
        grid.addWidget(self.secondary_combo, 1, 2)
        grid.addWidget(QLabel("بداية البيانات"), 2, 0)
        self.start_row = NumericSpinBox()
        self.start_row.setRange(0, 1_000_000)
        self.start_row.setSpecialValueText("تلقائي")
        grid.addWidget(self.start_row, 3, 0)
        grid.addWidget(QLabel("نهاية البيانات"), 2, 1)
        self.end_row = NumericSpinBox()
        self.end_row.setRange(0, 1_000_000)
        self.end_row.setSpecialValueText("آخر صف")
        grid.addWidget(self.end_row, 3, 1)
        layout.addLayout(grid)
        self.confidence = QLabel("", objectName="muted")
        layout.addWidget(self.confidence)
        self.data_preview = QTableWidget()
        self.data_preview.verticalHeader().hide()
        self.data_preview.setAlternatingRowColors(True)
        self.data_preview.setMaximumHeight(220)
        layout.addWidget(self.data_preview)
        return page

    def _folders_step(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("حدد مصدر الصور ووجهة آمنة للنتائج", objectName="sectionTitle"))
        self.source_zone = DropZone("مجلد الصور", "folder")
        self.source_zone.pathDropped.connect(self.set_source_path)
        self.destination_zone = DropZone("مجلد النتائج", "folder")
        self.destination_zone.pathDropped.connect(self.set_destination_path)
        layout.addWidget(self.source_zone)
        layout.addWidget(self.destination_zone)
        actions = QHBoxLayout()
        source = QPushButton("اختيار المصدر")
        source.clicked.connect(self._choose_source)
        destination = QPushButton("اختيار الوجهة")
        destination.clicked.connect(self._choose_destination)
        actions.addWidget(source)
        actions.addWidget(destination)
        actions.addStretch()
        layout.addLayout(actions)
        self.recursive = QCheckBox("البحث داخل المجلدات الفرعية")
        self.recursive.setChecked(True)
        layout.addWidget(self.recursive)
        return page

    def _rules_step(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(
            QLabel("المطابقة الدقيقة هي الافتراضية؛ فعّل فقط التحويلات التي تحتاجها", objectName="sectionTitle")
        )
        row = QHBoxLayout()
        row.addWidget(QLabel("نمط المطابقة"))
        self.match_mode = QComboBox()
        for value, title in [
            ("exact", "مطابقة دقيقة"),
            ("normalized", "دقيقة بعد تطبيع معتمد"),
            ("pattern", "مطابقة بقواعد النمط"),
            ("fuzzy", "اقتراحات تقريبية للمراجعة"),
        ]:
            self.match_mode.addItem(title, value)
        row.addWidget(self.match_mode)
        row.addStretch()
        layout.addLayout(row)
        normalization = QGridLayout()
        self.norm_checks: dict[str, QCheckBox] = {}
        labels = [
            ("unicode_forms", "توحيد أشكال Unicode"),
            ("arabic_digits_to_western", "تحويل الأرقام العربية إلى غربية"),
            ("remove_invisible", "حذف محارف التحكم غير المرئية"),
            ("collapse_spaces", "دمج المسافات الداخلية المتكررة"),
            ("normalize_dashes", "توحيد أشكال الشرطة"),
            ("dash_underscore_equivalent", "اعتبار الشرطة والشرطة السفلية متساويتين"),
        ]
        for index, (key, text) in enumerate(labels):
            check = QCheckBox(text)
            self.norm_checks[key] = check
            normalization.addWidget(check, index // 2, index % 2)
        layout.addLayout(normalization)
        fuzzy_row = QHBoxLayout()
        fuzzy_row.addWidget(QLabel("الحد الأدنى للاقتراح التقريبي"))
        self.fuzzy_threshold = NumericDoubleSpinBox()
        self.fuzzy_threshold.setRange(0.5, 0.99)
        self.fuzzy_threshold.setSingleStep(0.01)
        self.fuzzy_threshold.setValue(0.82)
        fuzzy_row.addWidget(self.fuzzy_threshold)
        fuzzy_row.addStretch()
        layout.addLayout(fuzzy_row)
        layout.addWidget(QLabel("مختبر قواعد أسماء الملفات", objectName="sectionTitle"))
        self.rules_table = QTableWidget(0, 4)
        self.rules_table.verticalHeader().hide()
        self.rules_table.setAlternatingRowColors(True)
        self.rules_table.setHorizontalHeaderLabels(["النوع", "القيمة", "البديل", "التطبيق على"])
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.rules_table)
        rule_actions = QHBoxLayout()
        for text, slot in [
            ("إضافة قاعدة", self._add_rule),
            ("حذف القاعدة", self._remove_rule),
            ("رفع", lambda: self._move_rule(-1)),
            ("خفض", lambda: self._move_rule(1)),
            ("إعادة الضبط", self._reset_rules),
        ]:
            button = QPushButton(text)
            button.clicked.connect(slot)
            rule_actions.addWidget(button)
        rule_actions.addStretch()
        layout.addLayout(rule_actions)
        options = QGridLayout()
        options.addWidget(QLabel("الملف الموجود"), 0, 0)
        self.duplicate_policy = QComboBox()
        for key, value in DUPLICATE_POLICY_AR.items():
            self.duplicate_policy.addItem(value, key)
        options.addWidget(self.duplicate_policy, 1, 0)
        options.addWidget(QLabel("التطابقات المتعددة"), 0, 1)
        self.multiple_policy = QComboBox()
        for key, value in MULTIPLE_POLICY_AR.items():
            self.multiple_policy.addItem(value, key)
        options.addWidget(self.multiple_policy, 1, 1)
        self.hash_check = QCheckBox("التحقق باستخدام SHA-256")
        self.report_check = QCheckBox("إنشاء تقرير Excel")
        self.report_check.setChecked(True)
        options.addWidget(self.hash_check, 2, 0)
        options.addWidget(self.report_check, 2, 1)
        options.addWidget(QLabel("قالب مجلد الوجهة"), 3, 0)
        self.folder_template = QLineEdit()
        self.folder_template.setPlaceholderText("مثال: {excel_name}/{date}")
        options.addWidget(self.folder_template, 4, 0)
        options.addWidget(QLabel("قالب اسم الملف"), 3, 1)
        self.filename_template = QLineEdit()
        self.filename_template.setPlaceholderText("مثال: {identifier}_{sequence}.{extension}")
        options.addWidget(self.filename_template, 4, 1)
        layout.addLayout(options)
        return page

    def _preview_step(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("شغّل المعاينة والفحص القبلي ثم راجع النتائج بصرياً", objectName="sectionTitle"))
        self.preview_summary = QLabel("لم تُنفّذ المعاينة بعد.", objectName="muted")
        layout.addWidget(self.preview_summary)
        self.preflight_table = QTableWidget(0, 3)
        self.preflight_table.verticalHeader().hide()
        self.preflight_table.setAlternatingRowColors(True)
        self.preflight_table.setHorizontalHeaderLabels(["الفحص", "الحالة", "التفاصيل"])
        self.preflight_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.preflight_table)
        preview = QPushButton("تشغيل المعاينة والفحص القبلي", objectName="primary")
        preview.clicked.connect(self._request_preview)
        layout.addWidget(preview)
        return page

    def _execute_step(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("المراجعة النهائية", objectName="sectionTitle"))
        self.review_label = QLabel("أكمل المعاينة أولاً.")
        self.review_label.setWordWrap(True)
        layout.addWidget(self.review_label)
        actions = QHBoxLayout()
        self.copy_button = QPushButton("بدء النسخ الحقيقي", objectName="primary")
        self.copy_button.clicked.connect(lambda: self._execute(False))
        self.dry_button = QPushButton("محاكاة دون نسخ")
        self.dry_button.clicked.connect(lambda: self._execute(True))
        self.copy_button.setEnabled(False)
        self.dry_button.setEnabled(False)
        self.pause_button = QPushButton("إيقاف مؤقت")
        self.pause_button.setCheckable(True)
        self.pause_button.clicked.connect(self._pause)
        self.cancel_button = QPushButton("إلغاء")
        self.cancel_button.clicked.connect(self.cancelRequested)
        actions.addWidget(self.copy_button)
        actions.addWidget(self.dry_button)
        actions.addWidget(self.pause_button)
        actions.addWidget(self.cancel_button)
        layout.addLayout(actions)
        self.stage = QLabel("جاهز")
        self.stage.setObjectName("sectionTitle")
        self.progress = QProgressBar()
        self.progress.setObjectName("operationProgress")
        self.progress.setRange(0, 100)
        self.progress_detail = QLabel("", objectName="muted")
        layout.addWidget(self.stage)
        layout.addWidget(self.progress)
        layout.addWidget(self.progress_detail)
        layout.addStretch()
        return page

    def go_to(self, step: int) -> None:
        self.current_step = max(0, min(len(self.STEPS) - 1, step))
        self.stack.setCurrentIndex(self.current_step)
        for index, button in enumerate(self.step_buttons):
            button.setProperty("complete", index < self.current_step)
            button.setProperty("current", index == self.current_step)
            button.style().unpolish(button)
            button.style().polish(button)
        self.back_button.setEnabled(self.current_step > 0)
        self.next_button.setVisible(self.current_step < len(self.STEPS) - 1)

    def set_theme(self, theme: str) -> None:
        self.excel_zone.set_theme(theme)
        self.source_zone.set_theme(theme)
        self.destination_zone.set_theme(theme)
        self.back_button.setIcon(icon("panel-right", theme=theme))
        self.next_button.setIcon(icon("panel-right", theme=theme, role="text_on_primary"))
        self.copy_button.setIcon(icon("plus", theme=theme, role="text_on_primary"))

    def _next(self) -> None:
        error = self._step_error(self.current_step)
        if error:
            message_dialog(self, "بيانات غير مكتملة", error, severity="warning").exec()
            return
        self.go_to(self.current_step + 1)

    def _step_error(self, step: int) -> str:
        if step == 0 and (not self.excel_path or not isinstance(self.column_combo.currentData(), ColumnInfo)):
            return "اختر ملف بيانات وعمود معرّف صالحاً."
        if step == 1 and (
            not self.source_path
            or not self.destination_path
            or self.source_path.resolve() == self.destination_path.resolve()
        ):
            return "اختر مصدراً ووجهة مختلفين."
        return ""

    def _choose_excel(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "اختيار ملف بيانات", str(Path.home()), "ملفات البيانات (*.xlsx *.xlsm *.csv *.tsv)"
        )
        if filename:
            self.set_excel_path(Path(filename))

    def set_excel_path(self, path: Path) -> None:
        try:
            info = self.excel.workbook_info(path)
        except Exception as exc:
            message_dialog(self, "ملف غير صالح", str(exc), severity="warning").exec()
            return
        self.excel_path = path
        self.excel_zone.set_path(path)
        self.sheet_combo.clear()
        self.sheet_combo.addItems(info.worksheets)
        self.sheet_combo.setCurrentText(info.active_worksheet)
        self._load_columns()
        self._invalidate_preview()

    def _load_columns(self) -> None:
        if not self.excel_path or not self.sheet_combo.currentText():
            return
        try:
            columns = self.excel.columns(self.excel_path, self.sheet_combo.currentText())
            scores = self.excel.score_columns(self.excel_path, self.sheet_combo.currentText(), columns)
            preview = self.excel.preview_rows(self.excel_path, self.sheet_combo.currentText(), 12)
        except Exception as exc:
            message_dialog(self, "تعذر قراءة البيانات", str(exc), severity="warning").exec()
            return
        self.column_combo.clear()
        self.secondary_combo.clear()
        self.secondary_combo.addItem("بدون عمود اسم", None)
        for column in columns:
            self.column_combo.addItem(column.display_name, column)
            self.secondary_combo.addItem(column.display_name, column)
        if scores:
            best = scores[0]
            index = next(
                (
                    i
                    for i in range(self.column_combo.count())
                    if self.column_combo.itemData(i).index == best.column.index
                ),
                0,
            )
            self.column_combo.setCurrentIndex(index)
            self.confidence.setText(f"الترشيح: {best.confidence} ({best.score:.1f}/100) — {'، '.join(best.reasons)}")
        width = max((len(row) for row in preview), default=0)
        self.data_preview.setColumnCount(width)
        self.data_preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.data_preview.setRowCount(len(preview))
        for row_index, row in enumerate(preview):
            for column_index, value in enumerate(row):
                self.data_preview.setItem(row_index, column_index, QTableWidgetItem(value))

    def _choose_source(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "اختيار مجلد الصور", str(Path.home()))
        if folder:
            self.set_source_path(Path(folder))

    def _choose_destination(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "اختيار مجلد النتائج", str(Path.home()))
        if folder:
            self.set_destination_path(Path(folder))

    def set_source_path(self, path: Path) -> None:
        self.source_path = path
        self.source_zone.set_path(path)
        self._invalidate_preview()

    def set_destination_path(self, path: Path) -> None:
        self.destination_path = path
        self.destination_zone.set_path(path)
        self._invalidate_preview()

    def _add_rule(self) -> None:
        kinds = {
            "إزالة بادئة": "remove_prefix",
            "إزالة لاحقة": "remove_suffix",
            "إزالة نص": "remove_text",
            "استبدال": "replace",
            "التقاط Regex": "regex_capture",
        }
        label, ok = QInputDialog.getItem(self, "إضافة قاعدة", "النوع:", list(kinds), editable=False)
        if not ok:
            return
        value, ok = QInputDialog.getText(self, "قيمة القاعدة", "النص أو التعبير:")
        if not ok:
            return
        replacement = ""
        if kinds[label] in {"replace", "regex_capture"}:
            replacement, _ = QInputDialog.getText(self, "البديل", "البديل أو رقم مجموعة الالتقاط:")
        self.rules.append(TransformationRule(kinds[label], value, replacement, True, "stem"))
        self._refresh_rules()
        self._invalidate_preview()

    def _remove_rule(self) -> None:
        row = self.rules_table.currentRow()
        if 0 <= row < len(self.rules):
            self.rules.pop(row)
            self._refresh_rules()
            self._invalidate_preview()

    def _move_rule(self, delta: int) -> None:
        row = self.rules_table.currentRow()
        target = row + delta
        if 0 <= row < len(self.rules) and 0 <= target < len(self.rules):
            self.rules[row], self.rules[target] = self.rules[target], self.rules[row]
            self._refresh_rules()
            self.rules_table.selectRow(target)

    def _reset_rules(self) -> None:
        self.rules.clear()
        self._refresh_rules()
        self._invalidate_preview()

    def _refresh_rules(self) -> None:
        self.rules_table.setRowCount(len(self.rules))
        for row, rule in enumerate(self.rules):
            for column, value in enumerate((rule.kind, rule.value, rule.replacement, rule.target)):
                self.rules_table.setItem(row, column, QTableWidgetItem(value))

    def build_settings(self, dry_run: bool = False) -> ProcessingSettings:
        if self._step_error(0) or self._step_error(1):
            raise ValueError("المدخلات غير مكتملة.")
        normalization = NormalizationOptions(**{key: check.isChecked() for key, check in self.norm_checks.items()})
        return ProcessingSettings(
            self.excel_path,
            self.sheet_combo.currentText(),
            self.column_combo.currentData(),
            self.source_path,
            self.destination_path,
            recursive=self.recursive.isChecked(),
            duplicate_policy=DuplicatePolicy(self.duplicate_policy.currentData()),
            multiple_match_policy=MultipleMatchPolicy(self.multiple_policy.currentData()),
            generate_report=self.report_check.isChecked(),
            matching_mode=MatchingMode(self.match_mode.currentData()),
            normalization=normalization,
            transformation_rules=list(self.rules),
            fuzzy_threshold=self.fuzzy_threshold.value(),
            secondary_column=self.secondary_combo.currentData(),
            start_row=self.start_row.value() or None,
            end_row=self.end_row.value() or None,
            dry_run=dry_run,
            destination_folder_template=self.folder_template.text().strip(),
            destination_filename_template=self.filename_template.text().strip(),
            verify_hash=self.hash_check.isChecked(),
            batch_name=self.excel_path.stem,
        )

    def _request_preview(self) -> None:
        try:
            settings = self.build_settings()
        except ValueError as exc:
            message_dialog(self, "بيانات ناقصة", str(exc), severity="warning").exec()
            return
        self.previewRequested.emit(settings)

    def set_preview_result(self, result: JobResult) -> None:
        self.preview_result = result
        self.preview_summary.setText(
            f"تمت المعاينة: {result.stats.valid_identifiers:,} معرّف؛ {result.stats.matched_identifiers:,} مطابق؛ {result.stats.unmatched_identifiers:,} غير موجود."
        )
        self.preflight_table.setRowCount(len(result.preflight_checks))
        labels = {"passed": "نجح", "warning": "تحذير", "failed": "فشل"}
        for row, check in enumerate(result.preflight_checks):
            for column, value in enumerate((check.title, labels[check.level.value], check.detail)):
                self.preflight_table.setItem(row, column, QTableWidgetItem(value))
        self.review_label.setText(
            f"ملف البيانات: {result.settings.excel_path}\nالمصدر: {result.settings.source_folder}\nالوجهة: {result.settings.destination_folder}\nالمطابق: {result.stats.matched_identifiers} | غير الموجود: {result.stats.unmatched_identifiers}\nلن يبدأ النسخ إلا عند ضغط «بدء النسخ الحقيقي»."
        )
        self.copy_button.setEnabled(not any(check.level.value == "failed" for check in result.preflight_checks))
        self.dry_button.setEnabled(True)
        self.go_to(3)

    def _execute(self, dry_run: bool) -> None:
        if not self.preview_result:
            message_dialog(self, "المعاينة مطلوبة", "شغّل المعاينة وراجع النتائج أولاً.", severity="warning").exec()
            return
        settings = self.build_settings(dry_run)
        self.simulation_banner.setVisible(dry_run)
        self.executeRequested.emit(settings, self.preview_result)

    def _pause(self, checked: bool) -> None:
        self.pause_button.setText("متابعة" if checked else "إيقاف مؤقت")
        self.pauseRequested.emit(checked)

    def set_processing(self, active: bool) -> None:
        self.copy_button.setEnabled(not active and self.preview_result is not None)
        self.dry_button.setEnabled(not active and self.preview_result is not None)
        self.cancel_button.setEnabled(active)
        self.pause_button.setEnabled(active)
        if not active:
            self.pause_button.setChecked(False)
            self.pause_button.setText("إيقاف مؤقت")

    def set_operation_state(self, state: OperationState) -> None:
        """Derive processing controls and visible status from one lifecycle state."""

        active_states = {
            OperationState.VALIDATING,
            OperationState.SCANNING,
            OperationState.MATCHING,
            OperationState.COPYING,
            OperationState.GENERATING_REPORT,
            OperationState.FINALIZING,
            OperationState.PAUSED,
        }
        self.set_processing(state in active_states)
        labels = {
            OperationState.IDLE: "جاهز",
            OperationState.VALIDATING: "جارٍ التحقق من المدخلات",
            OperationState.SCANNING: "جارٍ فهرسة الصور",
            OperationState.MATCHING: "جارٍ مطابقة المعرّفات",
            OperationState.COPYING: "جارٍ نسخ الصور",
            OperationState.GENERATING_REPORT: "جارٍ إنشاء التقرير",
            OperationState.FINALIZING: "جارٍ إنهاء العملية بأمان",
            OperationState.COMPLETED: "اكتملت العملية",
            OperationState.PARTIAL_SUCCESS: "اكتملت العملية مع ملاحظات",
            OperationState.FAILED: "تعذرت العملية",
            OperationState.CANCELLED: "تم إلغاء العملية",
            OperationState.PAUSED: "متوقف مؤقتًا",
        }
        self.stage.setText(labels[state])
        if state in {OperationState.COMPLETED, OperationState.PARTIAL_SUCCESS}:
            self.progress.setRange(0, 100)
            self.progress.setValue(100)

    def set_progress(self, stage: str, current: int, total: int, item: str, stats) -> None:
        self.stage.setText(stage)
        self.progress.setRange(0, 100 if total else 0)
        self.progress.setValue(round(current * 100 / total) if total else 0)
        self.progress_detail.setText(f"{current:,} / {total or '—'} — {item} — {stats.elapsed_seconds:.1f} ثانية")

    def _invalidate_preview(self) -> None:
        self.preview_result = None
        if hasattr(self, "preview_summary"):
            self.preview_summary.setText("تغيرت المدخلات؛ شغّل المعاينة مجدداً.")
        if hasattr(self, "copy_button"):
            self.copy_button.setEnabled(False)
            self.dry_button.setEnabled(False)

    def _wire_invalidation(self) -> None:
        for combo in (
            self.column_combo,
            self.secondary_combo,
            self.match_mode,
            self.duplicate_policy,
            self.multiple_policy,
        ):
            combo.currentIndexChanged.connect(self._invalidate_preview)
        for check in (self.recursive, self.hash_check, self.report_check, *self.norm_checks.values()):
            check.toggled.connect(self._invalidate_preview)
        for spin in (self.start_row, self.end_row, self.fuzzy_threshold):
            spin.valueChanged.connect(self._invalidate_preview)
        for field in (self.folder_template, self.filename_template):
            field.textChanged.connect(self._invalidate_preview)

    def load_demo(self, excel_path: Path, source_path: Path, destination_path: Path) -> None:
        """حمّل مساحة عرض خيالية من دون بدء المعالجة أو لمس ملفات المستخدم."""

        destination_path.mkdir(parents=True, exist_ok=True)
        self.set_excel_path(excel_path)
        self.set_source_path(source_path)
        self.set_destination_path(destination_path)
        self.recursive.setChecked(True)
        self.go_to(0)
