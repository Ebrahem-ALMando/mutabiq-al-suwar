"""Built-in illustrated Arabic guide and onboarding entry points."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from ui.icons import icon


class GuidePage(QWidget):
    tourRequested = Signal()
    demoRequested = Signal()

    STEPS = [
        ("1", "اختر ملف Excel", "حدّد ملف البيانات وتحقق من معاينة الأعمدة قبل المتابعة.", "spreadsheet.svg"),
        ("2", "حدّد عمود المعرّف", "اختر العمود الذي يحتوي الرقم أو الاسم المطابق للصورة.", "column.svg"),
        ("3", "أضف مصادر الصور", "أضف مجلداً واحداً أو أكثر؛ تبقى الملفات على جهازك.", "folders.svg"),
        ("4", "راجع المطابقات", "استخدم الجدول أو المعرض لتأكيد النتائج والاستثناءات.", "review.svg"),
        ("5", "انسخ وراجع التقرير", "اختر الوجهة، نفّذ النسخ، ثم افتح التقرير أو السجل.", "report.svg"),
    ]

    def __init__(self, project_root) -> None:
        super().__init__()
        self.project_root = project_root
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(4, 4, 16, 24)
        layout.setSpacing(18)

        hero = QFrame(objectName="hero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(28, 22, 28, 22)
        logo = QLabel()
        logo.setPixmap(
            QPixmap(str(project_root / "assets/branding/official_logo.png")).scaled(
                QSize(112, 76), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
        )
        text = QVBoxLayout()
        eyebrow = QLabel("الدليل التعليمي", objectName="eyebrow")
        title = QLabel("ابدأ عملية مطابقة موثوقة في خمس خطوات", objectName="pageTitle")
        detail = QLabel(
            "شرح محلي واضح يحافظ على خصوصية ملفاتك ويقودك من Excel حتى التقرير.", objectName="pageDescription"
        )
        detail.setWordWrap(True)
        actions = QHBoxLayout()
        self.tour_button = QPushButton("ابدأ الجولة التفاعلية", objectName="primary")
        self.demo_button = QPushButton("تحميل بيانات تجريبية")
        self.tour_button.clicked.connect(self.tourRequested)
        self.demo_button.clicked.connect(self.demoRequested)
        actions.addWidget(self.tour_button)
        actions.addWidget(self.demo_button)
        actions.addStretch()
        text.addWidget(eyebrow)
        text.addWidget(title)
        text.addWidget(detail)
        text.addLayout(actions)
        hero_layout.addLayout(text, 1)
        hero_layout.addWidget(logo)
        layout.addWidget(hero)

        steps = QGridLayout()
        steps.setHorizontalSpacing(14)
        steps.setVerticalSpacing(14)
        for index, (number, title_text, detail_text, illustration) in enumerate(self.STEPS):
            card = QFrame(objectName="card")
            card_layout = QVBoxLayout(card)
            image = QLabel()
            image.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image.setPixmap(
                QPixmap(str(project_root / "assets/illustrations/guide" / illustration)).scaled(
                    QSize(144, 92), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
            )
            heading = QLabel(f"{number}. {title_text}", objectName="sectionTitle")
            explanation = QLabel(detail_text, objectName="muted")
            explanation.setWordWrap(True)
            card_layout.addWidget(image)
            card_layout.addWidget(heading)
            card_layout.addWidget(explanation)
            steps.addWidget(card, index // 3, index % 3)
        layout.addLayout(steps)

        for title_text, detail_text in [
            ("أسئلة شائعة", "يمكن استخدام JPG وPNG وWebP وغيرها. المعالجة محلية ولا تُرفع الصور إلى أي خدمة."),
            ("حل المشكلات", "إن لم تظهر مطابقة، راجع تنسيق المعرّف وامتداد الصورة والمجلدات الفرعية ثم أعد المعاينة."),
            ("الخصوصية والاستعادة", "تُحفظ سجلات التشغيل محلياً. استخدم سجل العمليات لفتح التقرير أو التراجع الآمن."),
        ]:
            panel = QFrame(objectName="card")
            panel_layout = QVBoxLayout(panel)
            panel_layout.addWidget(QLabel(title_text, objectName="sectionTitle"))
            note = QLabel(detail_text, objectName="muted")
            note.setWordWrap(True)
            panel_layout.addWidget(note)
            layout.addWidget(panel)
        layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)

    def set_theme(self, theme: str) -> None:
        self.tour_button.setIcon(icon("book-open", theme=theme, role="text_on_primary"))
        self.demo_button.setIcon(icon("images", theme=theme))
