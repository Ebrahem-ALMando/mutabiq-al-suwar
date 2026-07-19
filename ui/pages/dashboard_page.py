"""لوحة مؤشرات مبنية على سجل SQLite الحقيقي."""

from __future__ import annotations

from PySide6.QtCore import Signal
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


class DashboardPage(QWidget):
    newOperationRequested = Signal()
    demoRequested = Signal()

    def __init__(self, history: HistoryRepository) -> None:
        super().__init__()
        self.history = history
        layout = QVBoxLayout(self)
        action_row = QHBoxLayout()
        intro = QLabel("ملخص نشاط المطابقة والنسخ المحلي", objectName="muted")
        start = QPushButton("بدء عملية جديدة", objectName="primary")
        start.clicked.connect(self.newOperationRequested)
        demo = QPushButton("تشغيل مساحة العرض")
        demo.clicked.connect(self.demoRequested)
        action_row.addWidget(intro)
        action_row.addStretch()
        action_row.addWidget(start)
        action_row.addWidget(demo)
        layout.addLayout(action_row)
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
        self.latest.setMaximumHeight(190)
        layout.addWidget(self.latest)
        self.refresh()

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
                ("مطابق", matched, "#16835B"),
                ("غير موجود", unmatched, "#B7791F"),
                ("متعدد", multiple, "#087B83"),
                ("فشل", failed, "#C2414B"),
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
