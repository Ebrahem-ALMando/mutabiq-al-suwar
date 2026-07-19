"""Capture deterministic light/dark UI previews for release visual inspection."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from main import load_application_font  # noqa: E402
from ui.dialogs import AppDialog  # noqa: E402
from ui.premium_window import MainWindow  # noqa: E402
from ui.theme import apply_application_theme  # noqa: E402
from utils.app_paths import AppPaths  # noqa: E402


def main() -> int:
    output = PROJECT_ROOT / "build" / "visual-check"
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    load_application_font(app)
    window = MainWindow(PROJECT_ROOT, AppPaths.create(output / "appdata"))
    window.resize(1360, 820)
    window.show()
    dialog = AppDialog(
        "اكتملت العملية مع ملاحظات",
        "تم نسخ الصور بنجاح، وتعذر إنشاء التقرير. بقي التطبيق مفتوحًا ويمكن بدء عملية جديدة.",
        severity="warning",
        details="المرجع: REPORT-001\nهذا نص تقني قابل للنسخ والقراءة.",
        primary_text="إغلاق",
        parent=window,
    )
    for theme in ("light", "dark"):
        apply_application_theme(app, theme)
        app.processEvents()
        window.grab().save(str(output / f"main-{theme}.png"))
        dialog.show()
        app.processEvents()
        dialog.grab().save(str(output / f"dialog-{theme}.png"))
        dialog.hide()
    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
