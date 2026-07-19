"""نقطة تشغيل تطبيق نسخ الصور حسب الرقم الذاتي."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTimer, Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QMessageBox

from services.logging_service import close_job_logger, create_job_logger
from ui.premium_window import MainWindow
from ui.theme import stylesheet
from utils.app_paths import AppPaths
from utils.constants import APP_ORGANIZATION, SETTINGS_APP_NAME
from utils.version import APP_VERSION


def project_root() -> Path:
    """أعد مجلد التطبيق في المصدر أو حزمة PyInstaller."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def asset_root() -> Path:
    """أعد مسار الأصول المضمّنة في المصدر أو PyInstaller."""

    bundle = getattr(sys, "_MEIPASS", None)
    return Path(bundle) / "assets" if bundle else project_root() / "assets"


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
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    load_application_font(app)
    app.setStyleSheet(stylesheet("light"))
    root = project_root()
    paths = AppPaths.create()
    logging.basicConfig(level=logging.INFO)
    startup_logger = None
    try:
        startup_logger, startup_log_path = create_job_logger(paths.logs)
        startup_logger.info("بدء تشغيل التطبيق %s؛ Python=%s؛ root=%s", APP_VERSION, sys.version, root)
        window = MainWindow(root, paths)
        window.show()
        if "--smoke-test" in sys.argv:
            QTimer.singleShot(700, app.quit)
        exit_code = app.exec()
        startup_logger.info("إغلاق التطبيق؛ exit_code=%d", exit_code)
        return exit_code
    except Exception:
        logging.exception("Fatal application startup error")
        QMessageBox.critical(None, "خطأ", "تعذر بدء التطبيق. راجع سجل النظام للتفاصيل.")
        return 1
    finally:
        if startup_logger:
            close_job_logger(startup_logger)


if __name__ == "__main__":
    raise SystemExit(main())
