"""Opt-in packaged smoke workflow that exercises two real worker lifecycles."""

from __future__ import annotations

import logging
import math
import tempfile
from pathlib import Path

from openpyxl import Workbook
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from models.result_models import ColumnInfo, DuplicatePolicy, ProcessingSettings
from services.processing_service import ProcessingService
from ui.components.inputs import NumericDoubleSpinBox, NumericSpinBox, spin_subcontrol_rects
from ui.premium_window import MainWindow
from ui.summary_dialog import SummaryDialog


def _exercise_corrected_ui(window: MainWindow, app: QApplication) -> None:
    """Exercise the corrected UI states before starting the worker lifecycle."""

    window.sidebar.set_reduced_motion(True)
    for key, button in window.sidebar.buttons.items():
        button.set_hover_progress(1.0)
        if not button.resolved_state_colors()["icon"].isValid():
            raise RuntimeError(f"invalid sidebar icon state: {key}")
        window.navigate(key)
        if not button.isChecked():
            raise RuntimeError(f"sidebar item did not activate: {key}")
        button.set_hover_progress(0.0)
        app.processEvents()

    was_expanded = window.sidebar.expanded
    window.sidebar.toggle()
    window.sidebar.toggle()
    if window.sidebar.expanded != was_expanded:
        raise RuntimeError("sidebar collapse/expand did not restore its state")
    for button in window.sidebar.buttons.values():
        if not button.rect().contains(button.content_rects()["icon"]):
            raise RuntimeError("sidebar icon escaped its interactive row")

    window.navigate("settings")
    fields = window.settings_page.findChildren(NumericSpinBox) + window.settings_page.findChildren(NumericDoubleSpinBox)
    if not fields:
        raise RuntimeError("numeric settings fields were not found")
    for field in fields:
        rects = spin_subcontrol_rects(field)
        if rects["editor"].intersects(rects["up"]) or rects["editor"].intersects(rects["down"]):
            raise RuntimeError("numeric editor overlaps step controls")
        original = field.value()
        field.stepUp()
        field.stepDown()
        if not math.isclose(float(field.value()), float(original), rel_tol=0.0, abs_tol=1e-9):
            raise RuntimeError("numeric step controls did not round-trip")

    for theme in ("light", "dark", "light"):
        window.apply_theme(theme)
        app.processEvents()
    window.navigate("operation")


def start_lifecycle_smoke(window: MainWindow, app: QApplication, logger: logging.Logger) -> None:
    """Run, dismiss, and repeat a tiny copy operation; exit nonzero on failure."""

    qt_messages: list[str] = []

    class _SmokeLogCapture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            qt_messages.append(record.getMessage())

    capture = _SmokeLogCapture()
    logger.addHandler(capture)
    temporary = tempfile.TemporaryDirectory(prefix="mutabiq-packaged-smoke-", ignore_cleanup_errors=True)
    root = Path(temporary.name)
    app.aboutToQuit.connect(temporary.cleanup)
    app.aboutToQuit.connect(lambda: logger.removeHandler(capture))
    source = root / "source"
    destination = root / "destination"
    source.mkdir()
    (source / "100.jpg").write_bytes(b"smoke-image")
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    sheet.append(["ID"])
    sheet.append(["100"])
    excel = root / "input.xlsx"
    workbook.save(excel)
    settings = ProcessingSettings(
        excel,
        "Data",
        ColumnInfo(1, "ID", "A"),
        source,
        destination,
        generate_report=False,
        duplicate_policy=DuplicatePolicy.RENAME,
    )
    prepared = ProcessingService().run(settings, True, logger)
    state = {"run": 1, "ticks": 0}
    window._lifecycle_smoke_state = (state, temporary)  # type: ignore[attr-defined]

    def fail(message: str) -> None:
        logger.error("Packaged lifecycle smoke failed: %s", message)
        QTimer.singleShot(0, lambda: app.exit(2))

    def poll() -> None:
        state["ticks"] += 1
        if state["ticks"] > 400:
            fail("timeout")
            return
        if not window.isVisible():
            fail("main window became invisible")
            return
        summaries = [dialog for dialog in window._dialogs if isinstance(dialog, SummaryDialog) and dialog.isVisible()]
        if summaries and not window.processing:
            summaries[0].reject()
            if window.worker_thread is not None:
                fail("thread reference remained after completion")
                return
            if state["run"] == 1:
                state["run"] = 2
                logger.info("Packaged lifecycle smoke: first operation passed; starting second")
                window._start(settings, False, prepared)
            else:
                copied = list(destination.glob("100*.jpg"))
                if len(copied) < 2:
                    fail("second operation did not produce a verified result")
                    return
                dangerous = [
                    message
                    for message in qt_messages
                    if ("qthread" in message.lower() and "destroyed" in message.lower())
                    or (
                        "deleted" in message.lower()
                        and ("qobject" in message.lower() or "c++ object" in message.lower())
                    )
                ]
                if dangerous:
                    fail(f"dangerous Qt lifecycle warning: {dangerous[-1]}")
                    return
                logger.info("Packaged lifecycle smoke passed; main visible after two operations")
                app.exit(0)
                return
        QTimer.singleShot(25, poll)

    try:
        _exercise_corrected_ui(window, app)
        logger.info("Packaged lifecycle smoke: corrected UI states passed")
    except Exception as exc:
        logger.exception("Packaged lifecycle smoke UI checks failed")
        fail(str(exc))
        return

    window._start(settings, False, prepared)
    QTimer.singleShot(25, poll)
