"""إعدادات فعلية للمظهر والأداء والخصوصية والفهرسة."""

from __future__ import annotations

import shutil

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from repositories.history_repository import HistoryRepository
from ui.components.inputs import NumericDoubleSpinBox, NumericSpinBox
from ui.dialogs import confirm_dialog, message_dialog
from utils.app_paths import AppPaths


class SettingsPage(QWidget):
    themeChanged = Signal(str)

    def __init__(self, settings: QSettings, paths: AppPaths, history: HistoryRepository) -> None:
        super().__init__()
        self.settings = settings
        self.paths = paths
        self.history = history
        layout = QHBoxLayout(self)
        self.categories = QListWidget()
        self.categories.addItems(
            [
                "المظهر",
                "المطابقة",
                "النسخ",
                "التقارير",
                "الفهرسة",
                "الأداء",
                "إمكانية الوصول",
                "الخصوصية",
                "النسخ الاحتياطي",
                "متقدم",
            ]
        )
        self.categories.setMaximumWidth(210)
        layout.addWidget(self.categories)
        self.stack = QStackedWidget()
        content_card = QFrame(objectName="card")
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(24, 22, 24, 22)
        content_layout.addWidget(self.stack)
        layout.addWidget(content_card, 1)
        self.theme = QComboBox()
        self.theme.addItem("فاتح", "light")
        self.theme.addItem("داكن", "dark")
        self.theme.setCurrentIndex(max(0, self.theme.findData(settings.value("theme", "light"))))
        self.theme.currentIndexChanged.connect(self._theme)
        self.large_text = QCheckBox("نص واجهة أكبر")
        self.large_text.setChecked(settings.value("large_text", False, type=bool))
        self.large_text.toggled.connect(lambda value: self._appearance("large_text", value))
        self.high_contrast = QCheckBox("تباين أعلى")
        self.high_contrast.setChecked(settings.value("high_contrast", False, type=bool))
        self.high_contrast.toggled.connect(lambda value: self._appearance("high_contrast", value))
        self.reduced_motion = QCheckBox("تقليل الحركة")
        self.reduced_motion.setChecked(settings.value("reduced_motion", False, type=bool))
        self.reduced_motion.toggled.connect(lambda value: self._appearance("reduced_motion", value))
        self.stack.addWidget(
            self._form_page(
                "المظهر",
                [("السمة", self.theme), ("", self.large_text), ("", self.high_contrast), ("", self.reduced_motion)],
            )
        )
        fuzzy = NumericDoubleSpinBox()
        fuzzy.setRange(0.5, 0.99)
        fuzzy.setValue(float(settings.value("fuzzy_threshold", 0.82)))
        fuzzy.valueChanged.connect(lambda value: settings.setValue("fuzzy_threshold", value))
        self.stack.addWidget(self._form_page("إعدادات المطابقة الافتراضية", [("حد الاقتراح التقريبي", fuzzy)]))
        retries = NumericSpinBox()
        retries.setRange(0, 10)
        retries.setValue(settings.value("retry_count", 2, type=int))
        retries.valueChanged.connect(lambda value: settings.setValue("retry_count", value))
        self.stack.addWidget(self._form_page("مرونة النسخ الشبكي", [("عدد المحاولات الإضافية", retries)]))
        self.stack.addWidget(self._label_page("التقارير", "تُحفظ تقارير Excel والمنشورات مع كل دفعة عند تفعيل الخيار."))
        index_page = QWidget()
        index_layout = QVBoxLayout(index_page)
        index_layout.addWidget(QLabel("المجلدات المفهرسة", objectName="sectionTitle"))
        self.index_label = QLabel()
        index_layout.addWidget(self.index_label)
        remove_index = QPushButton("حذف جميع الفهارس المحلية")
        remove_index.clicked.connect(self._clear_indexes)
        index_layout.addWidget(remove_index)
        index_layout.addStretch()
        self.stack.addWidget(index_page)
        self.stack.addWidget(
            self._label_page("الأداء", "تستخدم النتائج نموذج QAbstractTableModel، والفهرسة والنسخ في خيط خلفي.")
        )
        accessibility = self._label_page(
            "إمكانية الوصول",
            "استخدم خيارات النص الأكبر والتباين العالي وتقليل الحركة من قسم المظهر. تُحفظ الخيارات محلياً وتطبّق عند إعادة فتح التطبيق.",
        )
        self.stack.addWidget(accessibility)
        privacy = QWidget()
        privacy_layout = QVBoxLayout(privacy)
        privacy_layout.addWidget(QLabel("تتم المعالجة محلياً ولا تُرسل بيانات إلى الإنترنت."))
        clear_recent = QPushButton("مسح المسارات الأخيرة")
        clear_recent.clicked.connect(self._clear_recent)
        clear_history = QPushButton("مسح سجل العمليات فقط")
        clear_history.clicked.connect(self._clear_history)
        clear_thumbs = QPushButton("حذف ذاكرة الصور المصغرة")
        clear_thumbs.clicked.connect(self._clear_thumbnails)
        privacy_layout.addWidget(clear_recent)
        privacy_layout.addWidget(clear_history)
        privacy_layout.addWidget(clear_thumbs)
        privacy_layout.addStretch()
        self.stack.addWidget(privacy)
        self.stack.addWidget(self._label_page("النسخ الاحتياطي", f"مجلد النسخ الاحتياطية المحلية:\n{paths.backups}"))
        self.stack.addWidget(self._label_page("متقدم", f"قاعدة البيانات:\n{paths.database}"))
        self.categories.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.categories.setCurrentRow(0)
        self._update_indexes()

    @staticmethod
    def _form_page(title: str, rows: list[tuple[str, QWidget]]) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.addRow(QLabel(title, objectName="sectionTitle"))
        [form.addRow(label, widget) for label, widget in rows]
        return page

    @staticmethod
    def _label_page(title: str, text: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(title, objectName="sectionTitle"))
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addStretch()
        return page

    def _theme(self) -> None:
        value = self.theme.currentData()
        self.settings.setValue("theme", value)
        self.themeChanged.emit(value)

    def _appearance(self, key: str, value: bool) -> None:
        self.settings.setValue(key, value)
        self.themeChanged.emit(str(self.settings.value("theme", "light")))

    def _clear_recent(self) -> None:
        for key in ("last_excel_file", "last_excel_folder", "last_source_folder", "last_destination_folder"):
            self.settings.remove(key)
        message_dialog(self, "تم المسح", "تم مسح المسارات الأخيرة.", severity="success").exec()

    def _clear_history(self) -> None:
        if confirm_dialog(
            self,
            "تأكيد",
            "سيُمسح السجل فقط ولن تُحذف الصور أو التقارير. هل تتابع؟",
            confirm_text="مسح السجل",
            destructive=True,
        ):
            self.history.clear_history()

    def _clear_thumbnails(self) -> None:
        if self.paths.thumbnails.exists():
            shutil.rmtree(self.paths.thumbnails)
            self.paths.thumbnails.mkdir(parents=True, exist_ok=True)

    def _clear_indexes(self) -> None:
        if not confirm_dialog(
            self, "حذف الفهارس", "لن تُحذف أي صور. هل تتابع؟", confirm_text="حذف الفهارس", destructive=True
        ):
            return
        with self.history.connect() as connection:
            connection.execute("DELETE FROM indexed_folders")
        self._update_indexes()

    def _update_indexes(self) -> None:
        self.index_label.setText(
            "\n".join(
                f"{row['absolute_path']} — {row['image_count']:,} صورة — {row['last_scan']}"
                for row in self.history.indexed_folders()
            )
            or "لا توجد مجلدات مفهرسة."
        )
