"""End-to-end Qt worker lifecycle regressions for the original native crash."""

import logging

from openpyxl import Workbook

from models.operation_state import OperationState
from models.result_models import ColumnInfo, DuplicatePolicy, ProcessingSettings
from services.processing_service import ProcessingService
from ui.dialogs import AppDialog
from ui.premium_window import MainWindow
from ui.summary_dialog import SummaryDialog
from utils.app_paths import AppPaths


def _job(tmp_path, count: int = 1) -> tuple[ProcessingSettings, object]:
    excel = tmp_path / "input.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    sheet.append(["ID"])
    source = tmp_path / "source"
    source.mkdir(exist_ok=True)
    for index in range(count):
        identifier = str(100 + index)
        sheet.append([identifier])
        (source / f"{identifier}.jpg").write_bytes(b"image")
    workbook.save(excel)
    settings = ProcessingSettings(
        excel,
        "Data",
        ColumnInfo(1, "ID", "A"),
        source,
        tmp_path / "destination",
        generate_report=False,
        duplicate_policy=DuplicatePolicy.RENAME,
    )
    prepared = ProcessingService().run(settings, True, logging.getLogger("gui-preparation"))
    return settings, prepared


def _window(qtbot, tmp_path) -> MainWindow:
    window = MainWindow(tmp_path, AppPaths.create(tmp_path / "appdata"))
    qtbot.addWidget(window)
    window.show()
    return window


def test_success_dialog_closes_independently_and_second_operation_runs(qtbot, tmp_path) -> None:
    window = _window(qtbot, tmp_path)
    settings, prepared = _job(tmp_path)
    window._start(settings, False, prepared)
    qtbot.waitUntil(lambda: not window.processing, timeout=10000)
    assert window.isVisible()
    assert window.worker_thread is None
    assert window.operation_state == OperationState.COMPLETED
    dialog = next(dialog for dialog in window._dialogs if isinstance(dialog, SummaryDialog))
    assert dialog.isVisible()
    dialog.reject()
    qtbot.waitUntil(lambda: dialog not in window._dialogs)
    assert window.isVisible()

    window._start(settings, False, prepared)
    qtbot.waitUntil(lambda: not window.processing, timeout=10000)
    assert window.isVisible()
    assert window.worker_thread is None
    assert window.operation_state == OperationState.COMPLETED


def test_failure_keeps_window_open_and_controls_recover(qtbot, tmp_path) -> None:
    window = _window(qtbot, tmp_path)
    settings, _prepared = _job(tmp_path)
    settings.excel_path = tmp_path / "missing.xlsx"
    window._start(settings, False, None)
    qtbot.waitUntil(lambda: not window.processing, timeout=10000)
    assert window.isVisible()
    assert window.operation_state == OperationState.FAILED
    assert any(isinstance(dialog, AppDialog) and dialog.isVisible() for dialog in window._dialogs)
    assert window.operation.copy_button.isEnabled() is False or window.operation.preview_result is None


def test_immediate_cancellation_keeps_window_open(qtbot, tmp_path) -> None:
    window = _window(qtbot, tmp_path)
    settings, prepared = _job(tmp_path, count=20)
    window._start(settings, False, prepared)
    window.cancel()
    qtbot.waitUntil(lambda: not window.processing, timeout=10000)
    assert window.isVisible()
    assert window.worker_thread is None
    assert window.operation_state == OperationState.CANCELLED


def test_report_failure_is_partial_and_main_window_stays_open(qtbot, tmp_path, monkeypatch) -> None:
    window = _window(qtbot, tmp_path)
    settings, prepared = _job(tmp_path)
    settings.generate_report = True

    def fail_report(_self, _result):
        raise OSError("simulated GUI report failure")

    monkeypatch.setattr("services.report_service.ReportService.create", fail_report)
    window._start(settings, False, prepared)
    qtbot.waitUntil(lambda: not window.processing, timeout=10000)
    assert window.isVisible()
    assert window.operation_state == OperationState.PARTIAL_SUCCESS
    assert window.preview.result.report_error
    assert window.preview.result.stats.copied_files == 1
    assert any(isinstance(dialog, SummaryDialog) and dialog.isVisible() for dialog in window._dialogs)
