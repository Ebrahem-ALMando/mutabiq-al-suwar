"""هيكل التطبيق التجاري: شريط جانبي، شريط علوي، وصفحات مستقلة."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QThread
from PySide6.QtGui import QCloseEvent, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from models.result_models import JobResult, ProcessingSettings
from repositories.history_repository import HistoryRepository
from ui.components.sidebar import Sidebar
from ui.pages.about_page import AboutPage
from ui.pages.dashboard_page import DashboardPage
from ui.pages.history_page import HistoryPage
from ui.pages.operation_page import OperationPage
from ui.pages.preview_page import PreviewPage
from ui.pages.reports_page import ReportsPage
from ui.pages.settings_page import SettingsPage
from ui.summary_dialog import SummaryDialog, open_path
from ui.theme import stylesheet
from utils.app_paths import AppPaths
from utils.constants import APP_NAME
from utils.version import APP_VERSION
from workers.copy_worker import CopyWorker

PAGE_META = {
    "home": ("الرئيسية", "مؤشرات العمليات الأخيرة ونسب المطابقة"),
    "operation": ("عملية جديدة", "معالج واضح من اختيار البيانات حتى النسخ"),
    "preview": ("المعاينة والمطابقة", "راجع الصور واتخذ القرارات اليدوية قبل النسخ"),
    "history": ("سجل العمليات", "أعد فتح الدفعات أو صدّر منشورها أو تراجع بأمان"),
    "reports": ("التقارير", "الوصول إلى تقارير Excel ومنشورات التدقيق"),
    "settings": ("الإعدادات", "المظهر والأداء والفهرسة والخصوصية"),
    "about": ("حول البرنامج", "الإصدار والخصوصية والتوثيق المحلي"),
}


class CommandPalette(QDialog):
    """لوحة أوامر قابلة للبحث بالعربية واختصارات إنجليزية."""

    def __init__(self, commands: list[tuple[str, str, callable]], parent=None) -> None:
        super().__init__(parent)
        self.commands = commands
        self.filtered = commands
        self.setWindowTitle("لوحة الأوامر")
        self.setMinimumSize(560, 420)
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("اكتب أمراً... Ctrl+K")
        self.list = QListWidget()
        layout.addWidget(self.search)
        layout.addWidget(self.list)
        self.search.textChanged.connect(self._filter)
        self.list.itemActivated.connect(self._activate)
        self._filter("")
        self.search.setFocus()

    def _filter(self, text: str) -> None:
        query = text.casefold()
        self.filtered = [item for item in self.commands if query in f"{item[0]} {item[1]}".casefold()]
        self.list.clear()
        self.list.addItems([item[0] for item in self.filtered])

    def _activate(self, item) -> None:
        row = self.list.row(item)
        if 0 <= row < len(self.filtered):
            self.accept()
            self.filtered[row][2]()


class MainWindow(QMainWindow):
    """منسّق عرض صغير؛ تبقى منطقية الصفحات والخدمات خارج النافذة."""

    def __init__(self, project_root: Path, app_paths: AppPaths) -> None:
        super().__init__()
        self.project_root = project_root
        self.app_paths = app_paths
        self.settings = QSettings()
        self.history = HistoryRepository(app_paths.database)
        self.worker: CopyWorker | None = None
        self.thread: QThread | None = None
        self.processing = False
        self.current_page = "home"
        self.setWindowTitle(f"{APP_NAME} — {APP_VERSION}")
        self.setWindowIcon(QIcon(str(project_root / "assets/icons/app_logo.svg")))
        self.setMinimumSize(1120, 720)
        self.resize(1360, 820)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._build()
        self._shortcuts()
        self.apply_theme(self.settings.value("theme", "light"))
        geometry = self.settings.value("window_geometry")
        self.restoreGeometry(geometry) if geometry else None

    def _build(self) -> None:
        root = QWidget(objectName="appRoot")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        self.sidebar = Sidebar(
            str(self.project_root / "assets/icons/sidebar_logo.svg"),
            self.settings.value("reduced_motion", False, type=bool),
        )
        self.sidebar.pageSelected.connect(self.navigate)
        shell.addWidget(self.sidebar)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 12, 16, 14)
        content_layout.setSpacing(12)
        top = QFrame(objectName="topbar")
        top_layout = QHBoxLayout(top)
        title_box = QVBoxLayout()
        self.page_title = QLabel(objectName="pageTitle")
        self.page_description = QLabel(objectName="pageDescription")
        title_box.addWidget(self.page_title)
        title_box.addWidget(self.page_description)
        top_layout.addLayout(title_box)
        top_layout.addStretch()
        self.theme_button = QPushButton("السمة")
        self.theme_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon))
        self.theme_button.clicked.connect(self.toggle_theme)
        top_layout.addWidget(self.theme_button)
        self.notification_button = QPushButton("الإشعارات")
        self.notification_button.clicked.connect(self.show_notifications)
        top_layout.addWidget(self.notification_button)
        help_button = QPushButton("المساعدة")
        help_button.clicked.connect(
            lambda: open_path(
                self.project_root / "USER_GUIDE_AR.md"
                if (self.project_root / "USER_GUIDE_AR.md").exists()
                else self.project_root / "README.md"
            )
        )
        top_layout.addWidget(help_button)
        menu_button = QToolButton()
        menu_button.setText("القائمة")
        menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(menu_button)
        menu.addAction("لوحة الأوامر", self.show_command_palette)
        menu.addAction("فتح السجلات", lambda: open_path(self.app_paths.logs))
        menu.addAction("حول البرنامج", lambda: self.navigate("about"))
        menu_button.setMenu(menu)
        top_layout.addWidget(menu_button)
        content_layout.addWidget(top)
        self.pages = QStackedWidget()
        self.dashboard = DashboardPage(self.history)
        self.operation = OperationPage()
        self.preview = PreviewPage()
        self.history_page = HistoryPage(self.history)
        self.reports = ReportsPage(self.history)
        self.settings_page = SettingsPage(self.settings, self.app_paths, self.history)
        self.about = AboutPage(self.app_paths, self.project_root, self.project_root / "assets/icons/app_logo.svg")
        self.page_map = {
            "home": self.dashboard,
            "operation": self.operation,
            "preview": self.preview,
            "history": self.history_page,
            "reports": self.reports,
            "settings": self.settings_page,
            "about": self.about,
        }
        for page in self.page_map.values():
            self.pages.addWidget(page)
        content_layout.addWidget(self.pages, 1)
        shell.addWidget(content, 1)
        self.dashboard.newOperationRequested.connect(lambda: self.navigate("operation"))
        self.dashboard.demoRequested.connect(self.load_demo)
        self.operation.previewRequested.connect(lambda settings: self._start(settings, True, None))
        self.operation.executeRequested.connect(lambda settings, prepared: self._start(settings, False, prepared))
        self.operation.cancelRequested.connect(self.cancel)
        self.operation.pauseRequested.connect(self.pause)
        self.settings_page.themeChanged.connect(self.apply_theme)
        self.history_page.historyChanged.connect(self._refresh_pages)
        selected = self.settings.value("selected_page", "home")
        self.navigate(selected if selected in self.page_map else "home")
        self._update_notifications()

    def navigate(self, key: str) -> None:
        if key not in self.page_map:
            return
        self.current_page = key
        self.pages.setCurrentWidget(self.page_map[key])
        self.sidebar.select(key)
        self.page_title.setText(PAGE_META[key][0])
        self.page_description.setText(PAGE_META[key][1])
        self.settings.setValue("selected_page", key)
        if key == "home":
            self.dashboard.refresh()
        elif key == "history":
            self.history_page.refresh()
        elif key == "reports":
            self.reports.refresh()

    def _start(self, settings: ProcessingSettings, preview_only: bool, prepared: JobResult | None) -> None:
        if self.processing:
            return
        self.processing = True
        self.operation.set_processing(True)
        self.navigate("operation")
        self.thread = QThread(self)
        self.worker = CopyWorker(settings, preview_only, self.app_paths.logs, self.app_paths, prepared)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.operation.set_progress)
        self.worker.completed.connect(lambda result: self._completed(result, preview_only))
        self.worker.cancelled.connect(self._cancelled)
        self.worker.failed.connect(self._failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self._thread_finished)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _completed(self, result: JobResult, preview_only: bool) -> None:
        self.preview.set_result(result)
        self.operation.set_preview_result(result)
        if preview_only:
            self.navigate("preview")
            self.statusBar().showMessage("اكتملت المعاينة والفحص القبلي", 5000)
        else:
            self._refresh_pages()
            dialog = SummaryDialog(result, self)
            dialog.exec()
            self.navigate("history")
            self.statusBar().showMessage("اكتملت العملية وسُجل منشورها", 5000)
        self._update_notifications()

    def _cancelled(self, result: JobResult) -> None:
        self.preview.set_result(result)
        QMessageBox.information(self, "تم الإلغاء", "توقفت العملية بأمان وسُجلت الملفات المكتملة.")

    def _failed(self, message: str, log_path: str) -> None:
        QMessageBox.critical(
            self,
            "تعذر إكمال العملية",
            f"{message}\n\nالإجراء المقترح: راجع المسارات والصلاحيات ثم أعد المحاولة.\nالمرجع: PROC-001\nالسجل: {log_path}",
        )

    def _thread_finished(self) -> None:
        self.processing = False
        self.operation.set_processing(False)
        self.worker = None
        self.thread = None

    def cancel(self) -> None:
        if self.worker:
            self.worker.cancel()
            self.operation.stage.setText("جارٍ الإلغاء بأمان...")

    def pause(self, paused: bool) -> None:
        if self.worker:
            self.worker.pause() if paused else self.worker.resume()
            self.operation.stage.setText("متوقف مؤقتاً" if paused else "متابعة المعالجة")

    def apply_theme(self, theme: str) -> None:
        self.settings.setValue("theme", theme)
        QApplication.instance().setStyleSheet(
            stylesheet(
                theme,
                self.settings.value("large_text", False, type=bool),
                self.settings.value("high_contrast", False, type=bool),
            )
        )

    def toggle_theme(self) -> None:
        self.apply_theme("dark" if self.settings.value("theme", "light") == "light" else "light")

    def _update_notifications(self) -> None:
        self.notification_button.setText(f"الإشعارات ({len(self.history.active_notifications())})")

    def show_notifications(self) -> None:
        menu = QMenu(self)
        notifications = self.history.active_notifications()
        if not notifications:
            menu.addAction("لا توجد إشعارات")
        for item in notifications:
            menu.addAction(
                f"{item['title']} — {item['message']}", lambda checked=False, nid=item["id"]: self._dismiss(nid)
            )
        menu.exec(self.notification_button.mapToGlobal(self.notification_button.rect().bottomLeft()))

    def _dismiss(self, nid: int) -> None:
        self.history.dismiss_notification(nid)
        self._update_notifications()

    def _refresh_pages(self) -> None:
        self.dashboard.refresh()
        self.history_page.refresh()
        self.reports.refresh()

    def load_demo(self) -> None:
        """افتح البيانات الخيالية في المعالج ولا تبدأ أي إجراء تلقائياً."""

        self.operation.load_demo(
            self.project_root / "samples" / "sample_identifiers.xlsx",
            self.project_root / "samples" / "source_images",
            self.app_paths.root / "demo_output",
        )
        self.navigate("operation")

    def _shortcuts(self) -> None:
        bindings = [
            ("Ctrl+N", lambda: self.navigate("operation")),
            ("Ctrl+K", self.show_command_palette),
            ("Ctrl+P", lambda: self.operation._request_preview()),
            ("Ctrl+H", lambda: self.navigate("history")),
            ("Ctrl+,", lambda: self.navigate("settings")),
            ("Ctrl+D", self.toggle_theme),
            ("Ctrl+L", lambda: open_path(self.app_paths.logs)),
            ("F1", lambda: open_path(self.project_root / "README.md")),
            ("F5", self._refresh_pages),
        ]
        self.shortcuts = []
        for sequence, callback in bindings:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)

    def show_command_palette(self) -> None:
        commands = [
            ("عملية جديدة", "new operation", lambda: self.navigate("operation")),
            ("فتح المعاينة", "preview", lambda: self.navigate("preview")),
            ("سجل العمليات", "history", lambda: self.navigate("history")),
            ("الإعدادات", "settings", lambda: self.navigate("settings")),
            ("تبديل السمة", "toggle theme", self.toggle_theme),
            ("فتح السجلات", "logs", lambda: open_path(self.app_paths.logs)),
        ]
        CommandPalette(commands, self).exec()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.processing:
            if (
                QMessageBox.question(self, "عملية قيد التنفيذ", "هل تريد إلغاء العملية وانتظار توقفها قبل الإغلاق؟")
                != QMessageBox.StandardButton.Yes
            ):
                event.ignore()
                return
            self.cancel()
            if self.thread and not self.thread.wait(5000):
                QMessageBox.warning(self, "انتظار", "لم تتوقف العملية بعد. حاول بعد لحظات.")
                event.ignore()
                return
        self.settings.setValue("window_geometry", self.saveGeometry())
        event.accept()
