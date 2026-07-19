"""هيكل التطبيق التجاري: شريط جانبي، شريط علوي، وصفحات مستقلة."""

from __future__ import annotations

import logging
import traceback
import uuid
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt, QThread, Slot
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
    QPushButton,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from models.operation_state import OperationState
from models.result_models import JobResult, ProcessingSettings
from repositories.history_repository import HistoryRepository
from ui.animations import AnimationManager
from ui.components.controls import ThemeToggle
from ui.components.sidebar import Sidebar
from ui.dialogs import AppDialog, confirm_dialog, message_dialog
from ui.icons import icon
from ui.pages.about_page import AboutPage
from ui.pages.dashboard_page import DashboardPage
from ui.pages.guide_page import GuidePage
from ui.pages.history_page import HistoryPage
from ui.pages.operation_page import OperationPage
from ui.pages.preview_page import PreviewPage
from ui.pages.reports_page import ReportsPage
from ui.pages.settings_page import SettingsPage
from ui.summary_dialog import SummaryDialog, open_path
from ui.theme import apply_application_theme
from ui.tour import TourOverlay
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
PAGE_META["guide"] = ("الدليل التفاعلي", "تعلّم سير العمل خطوة بخطوة أو ابدأ جولة آمنة داخل الواجهة")


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

    def __init__(self, project_root: Path, app_paths: AppPaths, logger: logging.Logger | None = None) -> None:
        super().__init__()
        self.project_root = project_root
        self.app_paths = app_paths
        self.settings = QSettings()
        self.history = HistoryRepository(app_paths.database)
        self.logger = logger or logging.getLogger("mutabiq.lifecycle")
        self.worker: CopyWorker | None = None
        self.worker_thread: QThread | None = None
        self.processing = False
        self.operation_state = OperationState.IDLE
        self.active_operation_id: str | None = None
        self._terminal_seen: set[str] = set()
        self._operation_preview_modes: dict[str, bool] = {}
        self._pending_terminal: tuple[str, object, object | None] | None = None
        self._dialogs: list[QDialog] = []
        self._last_start: tuple[ProcessingSettings, bool, JobResult | None] | None = None
        self.logger.info("Main window creation started")
        self.current_page = "home"
        self.setWindowTitle(f"{APP_NAME} — {APP_VERSION}")
        self.setWindowIcon(QIcon(str(project_root / "assets/icons/app.ico")))
        self.setMinimumSize(1120, 720)
        self.resize(1360, 820)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.animations = AnimationManager(self.settings.value("reduced_motion", False, type=bool), self)
        self._build()
        self._shortcuts()
        self.apply_theme(self.settings.value("theme", "light"))
        geometry = self.settings.value("window_geometry")
        self.restoreGeometry(geometry) if geometry else None
        self.logger.info("Main window created; id=%s", id(self))

    def _build(self) -> None:
        root = QWidget(objectName="appRoot")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        self.sidebar = Sidebar(
            str(self.project_root / "assets/branding/official_logo.png"),
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
        self.theme_button = ThemeToggle(
            str(self.settings.value("theme", "light")),
            self.settings.value("reduced_motion", False, type=bool),
        )
        self.theme_button.themeChanged.connect(self.apply_theme)
        top_layout.addWidget(self.theme_button)
        self.notification_button = QPushButton("الإشعارات")
        self.notification_button.setObjectName("notificationButton")
        self.notification_button.setMaximumWidth(72)
        self.notification_button.setMinimumSize(42, 42)
        self.notification_button.setIconSize(QSize(24, 24))
        self.notification_button.setToolTip("الإشعارات")
        self.notification_button.clicked.connect(self.show_notifications)
        top_layout.addWidget(self.notification_button)
        self.help_button = QPushButton("")
        self.help_button.setObjectName("helpButton")
        self.help_button.setFixedWidth(44)
        self.help_button.setFixedHeight(44)
        self.help_button.setIconSize(QSize(24, 24))
        self.help_button.setToolTip("المساعدة والدليل")
        self.help_button.clicked.connect(lambda: self.navigate("guide"))
        top_layout.addWidget(self.help_button)
        menu_button = QToolButton()
        menu_button.setObjectName("mainMenuButton")
        menu_button.setText("")
        menu_button.setFixedWidth(44)
        menu_button.setFixedHeight(44)
        menu_button.setIconSize(QSize(24, 24))
        menu_button.setToolTip("القائمة")
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
        self.guide = GuidePage(self.project_root)
        self.about = AboutPage(
            self.app_paths, self.project_root, self.project_root / "assets/branding/official_logo.png"
        )
        self.page_map = {
            "home": self.dashboard,
            "operation": self.operation,
            "preview": self.preview,
            "history": self.history_page,
            "reports": self.reports,
            "guide": self.guide,
            "settings": self.settings_page,
            "about": self.about,
        }
        for page in self.page_map.values():
            self.pages.addWidget(page)
        content_layout.addWidget(self.pages, 1)
        shell.addWidget(content, 1)
        self.dashboard.newOperationRequested.connect(lambda: self.navigate("operation"))
        self.dashboard.demoRequested.connect(self.load_demo)
        self.guide.demoRequested.connect(self.load_demo)
        self.guide.tourRequested.connect(self.start_tour)
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
        self.animations.fade_in(self.page_map[key])
        if key == "home":
            self.dashboard.refresh()
        elif key == "history":
            self.history_page.refresh()
        elif key == "reports":
            self.reports.refresh()

    def _start(self, settings: ProcessingSettings, preview_only: bool, prepared: JobResult | None) -> None:
        if self.processing:
            self.logger.warning("Ignored duplicate start request; operation=%s", self.active_operation_id)
            return
        operation_id = str(uuid.uuid4())
        self._last_start = (settings, preview_only, prepared)
        self.active_operation_id = operation_id
        self._operation_preview_modes[operation_id] = preview_only
        self.processing = True
        self._set_state(OperationState.VALIDATING)
        self.navigate("operation")
        self.logger.info("Operation start; id=%s preview=%s", operation_id, preview_only)
        thread = QThread(self)
        worker = CopyWorker(settings, preview_only, self.app_paths.logs, self.app_paths, prepared, operation_id)
        self.worker_thread = thread
        self.worker = worker
        self.logger.info("Worker and thread created; id=%s worker=%s thread=%s", operation_id, id(worker), id(thread))
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._progress)
        worker.processing_completed.connect(self._processing_completed_signal)
        worker.processing_cancelled.connect(self._processing_cancelled_signal)
        worker.processing_failed.connect(self._processing_failed_signal)
        worker.worker_finished.connect(thread.quit)
        worker.worker_finished.connect(worker.deleteLater)
        thread.setProperty("operation_id", operation_id)
        thread.finished.connect(self._thread_finished_signal)
        thread.finished.connect(thread.deleteLater)
        self.logger.info("Lifecycle signals connected; id=%s", operation_id)
        thread.start()

    @Slot(str, str, int, int, str, object)
    def _progress(self, operation_id: str, stage: str, current: int, total: int, item: str, stats) -> None:
        if operation_id != self.active_operation_id or operation_id in self._terminal_seen:
            return
        stage_state = {
            "فهرسة": OperationState.SCANNING,
            "مطابقة": OperationState.MATCHING,
            "نسخ": OperationState.COPYING,
            "تقرير": OperationState.GENERATING_REPORT,
        }
        for text, state in stage_state.items():
            if text in stage:
                self._set_state(state)
                break
        self.operation.set_progress(stage, current, total, item, stats)

    @Slot(str, object)
    def _processing_completed_signal(self, operation_id: str, result: JobResult) -> None:
        preview_only = self._operation_preview_modes.get(operation_id, False)
        self._terminal(operation_id, "completed", result, preview_only)

    @Slot(str, object)
    def _processing_cancelled_signal(self, operation_id: str, result: JobResult) -> None:
        self._terminal(operation_id, "cancelled", result)

    @Slot(str, str, str)
    def _processing_failed_signal(self, operation_id: str, message: str, log_path: str) -> None:
        self._terminal(operation_id, "failed", message, log_path)

    def _terminal(self, operation_id: str, kind: str, payload: object, extra: object | None = None) -> None:
        """Record one terminal event; present UI only after the QThread has stopped."""

        try:
            if operation_id != self.active_operation_id or operation_id in self._terminal_seen:
                self.logger.warning("Ignored stale/duplicate terminal signal; id=%s kind=%s", operation_id, kind)
                return
            self._terminal_seen.add(operation_id)
            self._pending_terminal = (kind, payload, extra)
            self._set_state(OperationState.FINALIZING)
            self.logger.info("Worker terminal signal; id=%s kind=%s", operation_id, kind)
        except Exception:
            self.logger.exception("Terminal signal handler failed; id=%s", operation_id)
            self._pending_terminal = ("failed", "تعذر إنهاء العملية بصورة سليمة.", "")

    def _completed(self, result: JobResult, preview_only: bool) -> None:
        self.preview.set_result(result)
        self.operation.set_preview_result(result)
        if preview_only:
            self.navigate("preview")
            self.statusBar().showMessage("اكتملت المعاينة والفحص القبلي", 5000)
        else:
            self._refresh_pages()
            self.navigate("history")
            self.statusBar().showMessage("اكتملت العملية وسُجل منشورها", 5000)
            dialog = SummaryDialog(result, self)
            dialog.openFailed.connect(
                lambda message: self._show_dialog(message_dialog(self, "تعذر فتح المسار", message, severity="warning"))
            )
            self._show_dialog(dialog)
        self._update_notifications()

    def _cancelled(self, result: JobResult) -> None:
        self.preview.set_result(result)
        self._show_dialog(
            message_dialog(self, "تم الإلغاء", "توقفت العملية بأمان وسُجلت الملفات المكتملة.", severity="warning")
        )

    def _failed(self, message: str, log_path: str) -> None:
        dialog = AppDialog(
            "تعذر إكمال العملية",
            f"{message}\n\nراجع المسارات والصلاحيات ثم أعد المحاولة. المرجع: PROC-001",
            severity="error",
            details=f"المرجع: PROC-001\nالسجل: {log_path}",
            log_path=Path(log_path) if log_path else None,
            primary_text="إعادة المحاولة",
            secondary_text="إغلاق",
            parent=self,
        )
        dialog.actionTriggered.connect(
            lambda action: (
                self._retry_last() if action == "primary" else action == "open_log" and open_path(Path(log_path))
            )
        )
        self._show_dialog(dialog)

    def _retry_last(self) -> None:
        if not self.processing and self._last_start:
            settings, preview_only, prepared = self._last_start
            self._start(settings, preview_only, prepared)

    @Slot()
    def _thread_finished_signal(self) -> None:
        thread = self.sender()
        if not isinstance(thread, QThread):
            self.logger.error("Thread-finished signal had an unexpected sender")
            return
        self._thread_finished(str(thread.property("operation_id") or ""), thread)

    def _thread_finished(self, operation_id: str, thread: QThread) -> None:
        try:
            self.logger.info("Thread finished; id=%s", operation_id)
            if operation_id != self.active_operation_id or thread is not self.worker_thread:
                self.logger.warning("Ignored stale thread finish; id=%s", operation_id)
                return
            terminal = self._pending_terminal
            self.worker = None
            self.worker_thread = None
            self.processing = False
            self.operation.set_processing(False)
            self._pending_terminal = None
            self._operation_preview_modes.pop(operation_id, None)
            if terminal is None:
                terminal = ("failed", "انتهى خيط المعالجة دون نتيجة نهائية.", "")
            kind, payload, extra = terminal
            self.logger.info("Completion UI delivery started; id=%s kind=%s", operation_id, kind)
            if kind == "completed":
                result = payload
                assert isinstance(result, JobResult)
                self._set_state(
                    OperationState.PARTIAL_SUCCESS if result.outcome == "partial" else OperationState.COMPLETED
                )
                self._completed(result, bool(extra))
            elif kind == "cancelled":
                self._set_state(OperationState.CANCELLED)
                assert isinstance(payload, JobResult)
                self._cancelled(payload)
            else:
                self._set_state(OperationState.FAILED)
                self._failed(str(payload), str(extra or ""))
            self.logger.info("Completion UI delivery finished; id=%s", operation_id)
        except Exception:
            self.logger.exception("Thread cleanup/completion handler failed; id=%s", operation_id)
            self.processing = False
            self.worker = None
            self.worker_thread = None
            self.operation.set_processing(False)
            self._set_state(OperationState.FAILED)
            self._show_dialog(
                message_dialog(
                    self,
                    "خطأ غير متوقع",
                    "بقي التطبيق مفتوحًا، لكن تعذر عرض نتيجة العملية.",
                    severity="error",
                    details=traceback.format_exc(),
                )
            )

    def _set_state(self, state: OperationState) -> None:
        if self.operation_state != state:
            self.logger.info("Operation state: %s -> %s", self.operation_state.value, state.value)
        self.operation_state = state
        self.operation.set_operation_state(state)

    def _show_dialog(self, dialog: QDialog) -> None:
        """Open without a nested event loop and retain a stable reference."""

        self.logger.info("Dialog opening; class=%s", type(dialog).__name__)
        self._dialogs.append(dialog)
        dialog.finished.connect(lambda _code, owned=dialog: self._dialog_finished(owned))
        dialog.open()

    def _dialog_finished(self, dialog: QDialog) -> None:
        if dialog in self._dialogs:
            self._dialogs.remove(dialog)
        self.logger.info("Dialog closed; class=%s main_visible=%s", type(dialog).__name__, self.isVisible())

    def cancel(self) -> None:
        if self.worker:
            self.worker.cancel()
            self.operation.stage.setText("جارٍ الإلغاء بأمان...")

    def pause(self, paused: bool) -> None:
        if self.worker:
            self.worker.pause() if paused else self.worker.resume()
            self.operation.stage.setText("متوقف مؤقتاً" if paused else "متابعة المعالجة")

    def apply_theme(self, theme: str) -> None:
        try:
            self.settings.setValue("theme", theme)
            app = QApplication.instance()
            assert isinstance(app, QApplication)
            apply_application_theme(
                app,
                theme,
                self.settings.value("large_text", False, type=bool),
                self.settings.value("high_contrast", False, type=bool),
            )
            reduced = self.settings.value("reduced_motion", False, type=bool)
            self.animations.set_reduced_motion(reduced)
            self.sidebar.set_reduced_motion(reduced)
            self.theme_button.reduced_motion = reduced
            self.theme_button.set_theme(theme)
            self.sidebar.set_theme(theme)
            self.notification_button.setIcon(icon("bell", theme=theme, size=24))
            self.help_button.setIcon(icon("circle-help", theme=theme, size=24))
            menu_button = self.findChild(QToolButton, "mainMenuButton")
            if menu_button:
                menu_button.setIcon(icon("menu", theme=theme, size=24))
            for page in self.page_map.values():
                if hasattr(page, "set_theme"):
                    page.set_theme(theme)
            self.logger.info("Theme applied; theme=%s dialogs=%d", theme, len(self._dialogs))
        except Exception:
            self.logger.exception("Theme application failed; theme=%s", theme)

    def toggle_theme(self) -> None:
        self.apply_theme("dark" if self.settings.value("theme", "light") == "light" else "light")

    def start_tour(self) -> None:
        """Start a non-modal overlay; missing targets are handled gracefully."""
        self.navigate("home")
        self._tour = TourOverlay(
            self,
            [
                ("sidebar", "تنقّل بين أقسام التطبيق"),
                ("navButton", "ابدأ عملية جديدة"),
                ("pageTitle", "اعرف مكانك الحالي"),
                ("helpButton", "ارجع إلى الدليل في أي وقت"),
                ("notificationButton", "تابع نتائج العمليات والتنبيهات"),
            ],
        )
        self._tour.setGeometry(self.centralWidget().rect())
        self._tour.show()
        self._tour.raise_()
        self._tour.setFocus()

    def _update_notifications(self) -> None:
        count = len(self.history.active_notifications())
        self.notification_button.setText(f"{count}" if count else "")
        self.notification_button.setToolTip(f"الإشعارات ({count})")

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
        for name, refresh in (
            ("dashboard", self.dashboard.refresh),
            ("history", self.history_page.refresh),
            ("reports", self.reports.refresh),
        ):
            try:
                refresh()
            except Exception:
                self.logger.exception("Page refresh failed; page=%s", name)
                self.statusBar().showMessage("تعذر تحديث بعض بيانات السجل؛ بقيت نتائج النسخ محفوظة.", 7000)

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
        self.logger.info("Main-window close event; processing=%s", self.processing)
        if self.processing:
            if not confirm_dialog(
                self,
                "عملية قيد التنفيذ",
                "يمكن متابعة العملية، أو إلغاؤها بأمان ثم محاولة الخروج مجددًا.",
                confirm_text="إلغاء العملية ثم الخروج",
                cancel_text="متابعة العملية",
                destructive=True,
            ):
                event.ignore()
                return
            self.cancel()
            self._show_dialog(
                message_dialog(self, "جارٍ الإلغاء", "سيبقى التطبيق مفتوحًا حتى يتوقف العامل بأمان، ثم يمكنك إغلاقه.")
            )
            event.ignore()
            return
        self.settings.setValue("window_geometry", self.saveGeometry())
        self.logger.info("Main-window shutdown accepted")
        event.accept()
