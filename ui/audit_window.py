"""Developer-only component gallery exposed through ``--ui-audit``."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ui.components.controls import ThemeToggle
from ui.components.inputs import NumericDoubleSpinBox, NumericSpinBox
from ui.components.sidebar import SidebarNavItem
from ui.icons import icon, icon_names, icon_pixmap
from ui.theme import apply_application_theme, colors_for


class UiAuditWindow(QMainWindow):
    """Fictional values only; never appears in normal product navigation."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Mutabiq UI Audit")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(1366, 768)
        root = QWidget(objectName="appRoot")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        header = QHBoxLayout()
        header.addWidget(QLabel("معرض تدقيق المكوّنات", objectName="pageTitle"))
        header.addStretch()
        self.theme_toggle = ThemeToggle("light", reduced_motion=True)
        self.theme_toggle.themeChanged.connect(self.set_theme)
        header.addWidget(self.theme_toggle)
        layout.addLayout(header)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("auditTabs")
        self.tabs.addTab(self._sidebar_page(), "حالات الشريط")
        self.tabs.addTab(self._icon_page(), "شبكة الأيقونات")
        self.tabs.addTab(self._numeric_page(), "الحقول الرقمية")
        self.tabs.addTab(self._controls_page(), "الأزرار والحقول")
        layout.addWidget(self.tabs)
        self.set_theme("light")

    @staticmethod
    def _scroll_page() -> tuple[QScrollArea, QWidget, QVBoxLayout]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        scroll.setWidget(body)
        return scroll, body, layout

    def _sidebar_page(self) -> QScrollArea:
        scroll, _body, layout = self._scroll_page()
        self.sidebar_items: dict[str, SidebarNavItem] = {}
        states = [
            ("default", "افتراضي", False, 0.0, True, False),
            ("hover", "تحويم", False, 1.0, True, False),
            ("active", "نشط", True, 0.0, True, False),
            ("active_hover", "نشط مع تحويم", True, 1.0, True, False),
            ("focus", "تركيز لوحة المفاتيح", False, 0.0, True, False),
            ("disabled", "معطل", False, 0.0, False, False),
            ("collapsed", "مطوي", False, 0.0, True, True),
        ]
        for key, title, checked, hover, enabled, collapsed in states:
            row = QFrame(objectName="card")
            row_layout = QHBoxLayout(row)
            row_layout.addWidget(QLabel(title, objectName="sectionTitle"))
            row_layout.addStretch()
            item = SidebarNavItem("عملية جديدة", "plus")
            item.setFixedWidth(76 if collapsed else 260)
            item.setChecked(checked)
            item.set_hover_progress(hover)
            item.setEnabled(enabled)
            item.set_collapsed(collapsed)
            item.set_reduced_motion(True)
            row_layout.addWidget(item)
            self.sidebar_items[key] = item
            layout.addWidget(row)
        layout.addWidget(QLabel("جميع أيقونات الشريط", objectName="sectionTitle"))
        for key, label, icon_name in [
            ("home", "الرئيسية", "house"),
            ("operation", "عملية جديدة", "plus"),
            ("preview", "المعاينة والمطابقة", "images"),
            ("history", "سجل العمليات", "history"),
            ("reports", "التقارير", "file-chart"),
            ("guide", "الدليل التفاعلي", "book-open"),
            ("settings", "الإعدادات", "settings"),
            ("about", "حول البرنامج", "info"),
        ]:
            item = SidebarNavItem(label, icon_name)
            item.setObjectName(f"audit_{key}")
            item.setFixedWidth(260)
            item.set_reduced_motion(True)
            layout.addWidget(item, 0, Qt.AlignmentFlag.AlignRight)
        layout.addStretch()
        return scroll

    def _icon_page(self) -> QScrollArea:
        scroll, body, layout = self._scroll_page()
        self.icon_grid = QGridLayout()
        self.icon_labels: list[tuple[QLabel, str]] = []
        for index, name in enumerate(icon_names()):
            card = QFrame(objectName="card")
            card_layout = QVBoxLayout(card)
            visual = QLabel()
            visual.setAlignment(Qt.AlignmentFlag.AlignCenter)
            visual.setFixedSize(56, 56)
            card_layout.addWidget(visual, 0, Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(QLabel(name, objectName="muted"), 0, Qt.AlignmentFlag.AlignCenter)
            self.icon_labels.append((visual, name))
            self.icon_grid.addWidget(card, index // 6, index % 6)
        layout.addLayout(self.icon_grid)
        layout.addStretch()
        body.setObjectName("iconAuditPage")
        return scroll

    def _numeric_page(self) -> QScrollArea:
        scroll, body, layout = self._scroll_page()
        grid = QGridLayout()
        self.numeric_fields: list[NumericSpinBox | NumericDoubleSpinBox] = []

        examples: list[tuple[str, NumericSpinBox | NumericDoubleSpinBox]] = []
        for label, value in (("صفر", 0), ("سالب", -25), ("عدد كبير", 999999)):
            field = NumericSpinBox()
            field.setRange(-999999, 999999)
            field.setValue(value)
            examples.append((label, field))
        decimal = NumericDoubleSpinBox()
        decimal.setDecimals(2)
        decimal.setRange(-100, 100)
        decimal.setValue(0.82)
        examples.append(("قيمة عشرية 0.82", decimal))
        percent = NumericDoubleSpinBox()
        percent.setDecimals(2)
        percent.setRange(0, 100)
        percent.setValue(1.0)
        percent.setSuffix(" %")
        examples.append(("لاحقة نسبة", percent))
        prefix = NumericSpinBox()
        prefix.setRange(0, 999999)
        prefix.setValue(100)
        prefix.setPrefix("ID ")
        examples.append(("بادئة", prefix))
        disabled = NumericDoubleSpinBox()
        disabled.setValue(0.82)
        disabled.setEnabled(False)
        examples.append(("معطل", disabled))
        readonly = NumericDoubleSpinBox()
        readonly.setValue(0.82)
        readonly.setReadOnly(True)
        examples.append(("للقراءة فقط", readonly))

        for index, (label, field) in enumerate(examples):
            grid.addWidget(QLabel(label), index, 0)
            grid.addWidget(field, index, 1)
            self.numeric_fields.append(field)
        layout.addLayout(grid)
        layout.addStretch()
        body.setObjectName("numericAuditPage")
        return scroll

    def _controls_page(self) -> QScrollArea:
        scroll, _body, layout = self._scroll_page()
        utilities = QFrame(objectName="card")
        utility_layout = QHBoxLayout(utilities)
        self.utility_buttons: list[tuple[QToolButton, str]] = []
        for name, tooltip in (("menu", "القائمة"), ("circle-help", "المساعدة"), ("bell", "الإشعارات")):
            button = QToolButton()
            button.setObjectName("auditUtilityButton")
            button.setFixedSize(44, 44)
            button.setIconSize(QSize(24, 24))
            button.setToolTip(tooltip)
            self.utility_buttons.append((button, name))
            utility_layout.addWidget(button)
        self.audit_theme_toggle = ThemeToggle("light", reduced_motion=True)
        self.audit_theme_toggle.themeChanged.connect(self.set_theme)
        utility_layout.addWidget(self.audit_theme_toggle)
        utility_layout.addStretch()
        layout.addWidget(utilities)
        grid = QGridLayout()
        combo = QComboBox()
        combo.addItems(["اختيار عربي", "Excel A", "قيمة طويلة لا تتداخل مع السهم"])
        line = QLineEdit()
        line.setPlaceholderText("بحث لا يتداخل مع زر أو أيقونة")
        check = QCheckBox("خيار محدد")
        check.setChecked(True)
        radio = QRadioButton("اختيار دائري")
        radio.setChecked(True)
        progress = QProgressBar()
        progress.setValue(68)
        primary = QPushButton("إجراء أساسي", objectName="primary")
        disabled = QPushButton("زر معطل")
        disabled.setEnabled(False)
        for row, (label, widget) in enumerate(
            (
                ("قائمة", combo),
                ("بحث", line),
                ("", check),
                ("", radio),
                ("تقدم", progress),
                ("", primary),
                ("", disabled),
            )
        ):
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(widget, row, 1)
        layout.addLayout(grid)
        layout.addStretch()
        return scroll

    def set_theme(self, theme: str) -> None:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_application_theme(app, theme)
        self.theme_toggle.set_theme(theme)
        self.audit_theme_toggle.set_theme(theme)
        for item in self.findChildren(SidebarNavItem):
            item.set_theme(theme)
        c = colors_for(theme)
        ratio = max(1.0, self.devicePixelRatioF())
        for label, name in getattr(self, "icon_labels", []):
            label.setPixmap(icon_pixmap(name, color=c["text_primary"], size=32, ratio=ratio))
        for button, name in getattr(self, "utility_buttons", []):
            button.setIcon(icon(name, theme=theme, size=24))
