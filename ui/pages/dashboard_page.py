"""لوحة مؤشرات مبنية على سجل SQLite الحقيقي."""

from __future__ import annotations

from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
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
from ui.components.charts import BarChart, DonutChart
from ui.icons import icon, logo_icon


class DashboardPage(QWidget):
    newOperationRequested = Signal()
    demoRequested = Signal()

    def __init__(self, history: HistoryRepository) -> None:
        super().__init__()
        self.history = history
        layout = QVBoxLayout(self)
        hero = QFrame(objectName="hero")
        action_row = QHBoxLayout(hero)
        action_row.setContentsMargins(24, 18, 24, 18)
        emblem = QLabel()
        emblem.setPixmap(logo_icon().pixmap(QSize(100, 70)))
        intro_box = QVBoxLayout()
        intro_box.addWidget(QLabel("منصة المطابقة المحلية", objectName="eyebrow"))
        intro_box.addWidget(QLabel("طابق صورك بثقة، وراجع كل نتيجة قبل النسخ", objectName="sectionTitle"))
        intro = QLabel("سير عمل عربي واضح يحافظ على الملفات داخل جهازك.", objectName="muted")
        intro_box.addWidget(intro)
        action_row.addLayout(intro_box, 1)
        self.start = QPushButton("بدء عملية جديدة", objectName="heroPrimary")
        self.start.setProperty("tourTarget", "new-operation")
        self.start.clicked.connect(self.newOperationRequested)
        self.demo = QPushButton("تحميل مثال آمن")
        self.demo.clicked.connect(self.demoRequested)
        action_row.addWidget(self.start)
        action_row.addWidget(self.demo)
        action_row.addWidget(emblem)
        layout.addWidget(hero)
        self.stats_grid = QGridLayout()
        self.stat_values: dict[str, QLabel] = {}
        items = [
            ("batches", "الدفعات المكتملة"),
            ("identifiers", "المعرّفات"),
            ("matched", "المطابقة"),
            ("unmatched", "غير الموجودة"),
            ("match_rate", "نسبة المطابقة"),
            ("copied", "الملفات المنسوخة"),
            ("copied_bytes", "حجم البيانات"),
            ("average_seconds", "متوسط الزمن"),
        ]
        for index, (key, title) in enumerate(items):
            card = QFrame(objectName="card")
            card_layout = QVBoxLayout(card)
            card_layout.addWidget(QLabel(title, objectName="muted"))
            value = QLabel("0", objectName="statValue")
            card_layout.addWidget(value)
            self.stat_values[key] = value
            self.stats_grid.addWidget(card, index // 4, index % 4)
        layout.addLayout(self.stats_grid)
        chart_row = QHBoxLayout()
        distribution_card = QFrame(objectName="card")
        distribution_layout = QVBoxLayout(distribution_card)
        distribution_layout.addWidget(QLabel("توزيع المطابقة", objectName="sectionTitle"))
        self.distribution = DonutChart()
        distribution_layout.addWidget(self.distribution)
        chart_row.addWidget(distribution_card)
        history_card = QFrame(objectName="card")
        history_layout = QVBoxLayout(history_card)
        history_layout.addWidget(QLabel("حجم العمليات الأخيرة", objectName="sectionTitle"))
        self.history_chart = BarChart()
        history_layout.addWidget(self.history_chart)
        chart_row.addWidget(history_card)
        extension_card = QFrame(objectName="card")
        extension_layout = QVBoxLayout(extension_card)
        extension_layout.addWidget(QLabel("امتدادات الصور", objectName="sectionTitle"))
        self.extensions_chart = BarChart()
        extension_layout.addWidget(self.extensions_chart)
        chart_row.addWidget(extension_card)
        layout.addLayout(chart_row)
        layout.addWidget(QLabel("أحدث خمس عمليات", objectName="sectionTitle"))
        self.latest = QTableWidget(0, 5)
        self.latest.setHorizontalHeaderLabels(["التاريخ", "ملف البيانات", "المعرّفات", "المنسوخ", "الحالة"])
        self.latest.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.latest.verticalHeader().hide()
        self.latest.setAlternatingRowColors(True)
        self.latest.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.latest.setMaximumHeight(190)
        layout.addWidget(self.latest)
        self.refresh()

    def set_theme(self, theme: str) -> None:
        self.start.setIcon(icon("plus", theme=theme, role="text_on_gold"))
        self.demo.setIcon(icon("images", theme=theme))

    def refresh(self) -> None:
        data = self.history.dashboard()
        for key, label in self.stat_values.items():
            value = data.get(key, 0)
            if key == "match_rate":
                text = f"{value:.1f}%"
            elif key == "copied_bytes":
                text = self._size(value)
            elif key == "average_seconds":
                text = f"{value:.1f} ث"
            else:
                text = f"{value:,}"
            label.setText(text)
        series = self.history.history_series()
        matched = sum(item["matched_count"] for item in series)
        unmatched = sum(item["unmatched_count"] for item in series)
        multiple = sum(item["multiple_count"] for item in series)
        failed = sum(item["failed_count"] for item in series)
        self.distribution.set_values(
            [
                ("مطابق", matched, "success"),
                ("غير موجود", unmatched, "warning"),
                ("متعدد", multiple, "primary"),
                ("فشل", failed, "error"),
            ]
        )
        self.history_chart.set_values([(item["started_at"][5:10], item["total_identifiers"]) for item in series])
        self.extensions_chart.set_values(list(self.history.extension_distribution().items()))
        latest = self.history.recent_batches(5)
        self.latest.setRowCount(len(latest))
        for row, batch in enumerate(latest):
            for column, value in enumerate(
                (
                    batch["started_at"][:16].replace("T", " "),
                    batch["excel_filename"],
                    batch["total_identifiers"],
                    batch["copied_count"],
                    batch["status"],
                )
            ):
                self.latest.setItem(row, column, QTableWidgetItem(str(value)))

    @staticmethod
    def _size(value: int) -> str:
        size = float(value)
        for unit in ("ب", "ك.ب", "م.ب", "ج.ب"):
            if size < 1024 or unit == "ج.ب":
                return f"{size:.1f} {unit}"
            size /= 1024
        return str(value)
