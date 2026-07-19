"""Opt-in packaged smoke workflow that exercises two real worker lifecycles."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from openpyxl import Workbook
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from models.result_models import ColumnInfo, DuplicatePolicy, ProcessingSettings
from services.processing_service import ProcessingService
from ui.premium_window import MainWindow
from ui.summary_dialog import SummaryDialog


def start_lifecycle_smoke(window: MainWindow, app: QApplication, logger: logging.Logger) -> None:
    """Run, dismiss, and repeat a tiny copy operation; exit nonzero on failure."""

    temporary = tempfile.TemporaryDirectory(prefix="mutabiq-packaged-smoke-", ignore_cleanup_errors=True)
    root = Path(temporary.name)
    app.aboutToQuit.connect(temporary.cleanup)
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
        app.exit(2)

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
                logger.info("Packaged lifecycle smoke passed; main visible after two operations")
                app.exit(0)
                return
        QTimer.singleShot(25, poll)

    window._start(settings, False, prepared)
    QTimer.singleShot(25, poll)
