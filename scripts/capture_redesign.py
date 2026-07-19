"""Generate the complete redesign visual-regression matrix."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from main import load_application_font  # noqa: E402
from services.processing_service import ProcessingService  # noqa: E402
from ui.premium_window import MainWindow  # noqa: E402
from ui.summary_dialog import SummaryDialog  # noqa: E402
from utils.app_paths import AppPaths  # noqa: E402
from utils.constants import APP_ORGANIZATION, SETTINGS_APP_NAME  # noqa: E402


def settle(app: QApplication) -> None:
    for _ in range(3):
        QTest.qWait(20)
        app.processEvents()


def main() -> int:
    output = PROJECT_ROOT / "build" / "visual-check-redesign"
    output.mkdir(parents=True, exist_ok=True)
    QCoreApplication.setOrganizationName(APP_ORGANIZATION)
    QCoreApplication.setApplicationName(f"{SETTINGS_APP_NAME}-visual-check")
    QSettings().setValue("reduced_motion", True)
    app = QApplication([])
    load_application_font(app)
    paths = AppPaths.create(output / "appdata")
    window = MainWindow(PROJECT_ROOT, paths)
    window.load_demo()
    result = ProcessingService().run(
        window.operation.build_settings(dry_run=True),
        True,
        logging.getLogger("visual-check"),
    )
    window.operation.set_preview_result(result)
    window.preview.set_result(result)
    window.show()

    for width, height in ((1366, 768), (1920, 1080)):
        for theme in ("light", "dark"):
            target = output / f"{width}x{height}" / theme
            target.mkdir(parents=True, exist_ok=True)
            window.resize(width, height)
            window.apply_theme(theme)

            window.navigate("home")
            settle(app)
            window.grab().save(str(target / "dashboard.png"))

            window.navigate("operation")
            window.operation.go_to(0)
            settle(app)
            window.grab().save(str(target / "wizard.png"))

            window.navigate("preview")
            window.preview.tabs.setCurrentIndex(0)
            settle(app)
            window.grab().save(str(target / "preview-table.png"))

            window.preview.tabs.setCurrentIndex(1)
            settle(app)
            window.grab().save(str(target / "preview-gallery.png"))

            window.navigate("operation")
            window.operation.go_to(4)
            window.operation.set_progress("جارٍ نسخ الصور", 7, 12, "A-2026-15.png", result.stats)
            settle(app)
            window.grab().save(str(target / "progress.png"))

            completion = SummaryDialog(result, window)
            completion.show()
            settle(app)
            completion.grab().save(str(target / "completion.png"))
            completion.close()

            window.navigate("settings")
            settle(app)
            window.grab().save(str(target / "settings.png"))

            window.navigate("guide")
            settle(app)
            window.grab().save(str(target / "guide.png"))

    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
