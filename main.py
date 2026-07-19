"""نقطة تشغيل تطبيق نسخ الصور حسب الرقم الذاتي."""

from __future__ import annotations

import gc
import logging
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt, qInstallMessageHandler
from PySide6.QtGui import QFont, QFontDatabase, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from services.logging_service import close_job_logger, create_job_logger
from ui.dialogs import message_dialog
from ui.premium_window import MainWindow
from ui.theme import apply_application_theme
from utils.app_paths import AppPaths
from utils.constants import APP_ORGANIZATION, SETTINGS_APP_NAME
from utils.lifecycle_smoke import start_lifecycle_smoke
from utils.version import APP_VERSION


def project_root() -> Path:
    """أعد مجلد التطبيق في المصدر أو حزمة PyInstaller."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def asset_root() -> Path:
    """أعد مسار الأصول المضمّنة في المصدر أو PyInstaller."""

    return resource_root() / "assets"


def resource_root() -> Path:
    """Return the read-only resource root in source, one-folder, or one-file builds."""

    bundle = getattr(sys, "_MEIPASS", None)
    return Path(bundle) if bundle else project_root()


def load_application_font(app: QApplication) -> None:
    """حمّل خطوط Tajawal المحلية، أو استخدم خط نظام عربي مناسب."""

    font_directory = asset_root() / "fonts"
    loaded_families: list[str] = []
    for filename in ("Tajawal-Regular.ttf", "Tajawal-Medium.ttf", "Tajawal-Bold.ttf"):
        path = font_directory / filename
        if path.is_file():
            font_id = QFontDatabase.addApplicationFont(str(path))
            if font_id >= 0:
                loaded_families.extend(QFontDatabase.applicationFontFamilies(font_id))
    candidates = loaded_families + ["Tajawal", "Segoe UI", "Arial"]
    families = set(QFontDatabase.families())
    selected = next((family for family in candidates if family in families), app.font().family())
    app.setFont(QFont(selected, 10))


def main() -> int:
    """هيّئ التطبيق واعرض النافذة الرئيسية."""

    QCoreApplication.setOrganizationName(APP_ORGANIZATION)
    QCoreApplication.setApplicationName(SETTINGS_APP_NAME)
    QCoreApplication.setApplicationVersion(APP_VERSION)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    load_application_font(app)
    apply_application_theme(app, "light")
    root = resource_root()
    app.setWindowIcon(QIcon(str(root / "assets" / "icons" / "app.ico")))
    smoke_directory = (
        tempfile.TemporaryDirectory(prefix="mutabiq-smoke-data-", ignore_cleanup_errors=True)
        if "--smoke-test" in sys.argv
        else None
    )
    paths = AppPaths.create(Path(smoke_directory.name) / "appdata" if smoke_directory else None)
    logging.basicConfig(level=logging.INFO)
    startup_logger = None
    try:
        startup_logger, startup_log_path = create_job_logger(paths.logs)
        original_hook = sys.excepthook

        def exception_hook(exception_type, exception, traceback_object) -> None:
            startup_logger.exception(
                "Unhandled Python exception", exc_info=(exception_type, exception, traceback_object)
            )
            original_hook(exception_type, exception, traceback_object)

        def qt_message_handler(message_type, context, message) -> None:
            startup_logger.warning(
                "Qt message; type=%s file=%s line=%s message=%s",
                message_type,
                getattr(context, "file", ""),
                getattr(context, "line", 0),
                message,
            )

        sys.excepthook = exception_hook
        qInstallMessageHandler(qt_message_handler)
        startup_logger.info("بدء تشغيل التطبيق %s؛ Python=%s؛ root=%s", APP_VERSION, sys.version, root)
        splash = None
        if "--smoke-test" not in sys.argv:
            splash_pixmap = QPixmap(str(root / "assets" / "branding" / "official_logo.png"))
            if not splash_pixmap.isNull():
                splash = QSplashScreen(splash_pixmap)
                splash.showMessage(
                    "مُطابق الصور — تجهيز مساحة العمل",
                    Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
                    Qt.GlobalColor.white,
                )
                splash.show()
                app.processEvents()
        window = MainWindow(root, paths, startup_logger)
        window.show()
        if splash:
            splash.finish(window)
        if "--smoke-test" in sys.argv:
            start_lifecycle_smoke(window, app, startup_logger)
        exit_code = app.exec()
        if smoke_directory:
            window.close()
            window.deleteLater()
            app.processEvents()
            gc.collect()
        startup_logger.info("إغلاق التطبيق؛ exit_code=%d", exit_code)
        return exit_code
    except Exception:
        logging.exception("Fatal application startup error")
        message_dialog(None, "خطأ", "تعذر بدء التطبيق. راجع سجل النظام للتفاصيل.", severity="error").exec()
        return 1
    finally:
        if startup_logger:
            close_job_logger(startup_logger)
        if smoke_directory:
            smoke_directory.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
