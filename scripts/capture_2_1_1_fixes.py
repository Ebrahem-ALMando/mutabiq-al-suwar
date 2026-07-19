"""Capture the focused 2.1.1 visual-regression matrix."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QCoreApplication, QSettings, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QScrollArea  # noqa: E402

from main import load_application_font  # noqa: E402
from ui.audit_window import UiAuditWindow  # noqa: E402
from ui.premium_window import MainWindow  # noqa: E402
from utils.app_paths import AppPaths  # noqa: E402
from utils.constants import APP_ORGANIZATION, SETTINGS_APP_NAME  # noqa: E402

OUTPUT_ROOT = PROJECT_ROOT / "build" / "visual-check-redesign" / "2.1.1-fixes"
WINDOW_SIZES = ((1366, 768), (1920, 1080))


def settle(app: QApplication) -> None:
    for _ in range(5):
        QTest.qWait(25)
        app.processEvents()


def save_window(app: QApplication, window, path: Path) -> None:
    settle(app)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not window.grab().save(str(path)):
        raise RuntimeError(f"Could not save screenshot: {path}")


def configure_application(suffix: str) -> QApplication:
    QCoreApplication.setOrganizationName(APP_ORGANIZATION)
    QCoreApplication.setApplicationName(f"{SETTINGS_APP_NAME}-2.1.1-audit-{suffix}")
    settings = QSettings()
    settings.clear()
    settings.setValue("reduced_motion", True)
    settings.setValue("sidebar_collapsed", False)
    app = QApplication([])
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    load_application_font(app)
    return app


def capture_dpi(scale: float, width: int, height: int, output: Path) -> int:
    app = configure_application(f"dpi-{scale}")
    audit = UiAuditWindow()
    audit.resize(width, height)
    audit.tabs.setCurrentIndex(2)
    audit.show()
    save_window(app, audit, output)
    audit.close()
    return 0


def _audit_state_capture(
    app: QApplication,
    audit: UiAuditWindow,
    target: Path,
    state: str,
) -> None:
    audit.tabs.setCurrentIndex(0)
    item = audit.sidebar_items[state]
    page = audit.tabs.currentWidget()
    if isinstance(page, QScrollArea):
        page.ensureWidgetVisible(item, 40, 80)
    if state == "focus":
        audit.activateWindow()
        item.setFocus(Qt.FocusReason.TabFocusReason)
    save_window(app, audit, target)


def capture_size(app: QApplication, width: int, height: int) -> None:
    target = OUTPUT_ROOT / f"{width}x{height}"
    paths = AppPaths.create(OUTPUT_ROOT / "appdata" / f"{width}x{height}")
    window = MainWindow(PROJECT_ROOT, paths, logging.getLogger("capture-2.1.1"))
    window.resize(width, height)
    window.load_demo()
    window.show()

    window.apply_theme("light")
    window.navigate("operation")
    window.operation.go_to(0)
    save_window(app, window, target / "new-operation-light.png")

    window.apply_theme("dark")
    save_window(app, window, target / "new-operation-dark.png")

    window.apply_theme("light")
    operation = window.sidebar.buttons["operation"]
    operation.setChecked(False)
    operation.set_hover_progress(1.0)
    save_window(app, window, target / "operation-hovered.png")
    operation.setChecked(True)
    save_window(app, window, target / "operation-active.png")
    operation.set_hover_progress(0.0)
    window.navigate("home")
    save_window(app, window, target / "home-active.png")

    audit = UiAuditWindow()
    audit.resize(width, height)
    audit.show()
    audit.set_theme("light")
    for state, filename in (
        ("default", "sidebar-default.png"),
        ("hover", "sidebar-hover.png"),
        ("active", "sidebar-active.png"),
        ("active_hover", "sidebar-active-hover.png"),
        ("focus", "sidebar-focus.png"),
        ("collapsed", "sidebar-collapsed.png"),
    ):
        _audit_state_capture(app, audit, target / filename, state)

    audit.tabs.setCurrentIndex(1)
    audit.set_theme("light")
    save_window(app, audit, target / "icon-grid-light.png")
    audit.set_theme("dark")
    save_window(app, audit, target / "icon-grid-dark.png")

    audit.tabs.setCurrentIndex(2)
    audit.set_theme("light")
    save_window(app, audit, target / "numeric-fields-light.png")
    audit.set_theme("dark")
    save_window(app, audit, target / "numeric-fields-dark.png")

    audit.tabs.setCurrentIndex(3)
    audit.set_theme("light")
    save_window(app, audit, target / "top-utility-buttons.png")
    audit.close()
    window.close()


def spawn_dpi_captures() -> None:
    for width, height in WINDOW_SIZES:
        for percent, scale in ((125, 1.25), (150, 1.5), (200, 2.0)):
            output = OUTPUT_ROOT / f"{width}x{height}" / f"numeric-fields-{percent}.png"
            environment = os.environ.copy()
            environment["QT_SCALE_FACTOR"] = str(scale)
            subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--dpi",
                    str(scale),
                    "--width",
                    str(width),
                    "--height",
                    str(height),
                    "--output",
                    str(output),
                ],
                cwd=PROJECT_ROOT,
                env=environment,
                check=True,
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dpi", type=float)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.dpi:
        if args.width is None or args.height is None or args.output is None:
            raise SystemExit("--dpi requires --width, --height, and --output")
        return capture_dpi(args.dpi, args.width, args.height, args.output)

    app = configure_application("main")
    for width, height in WINDOW_SIZES:
        capture_size(app, width, height)
    spawn_dpi_captures()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
