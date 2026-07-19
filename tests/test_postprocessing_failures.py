import logging

from openpyxl import Workbook

from models.result_models import ColumnInfo, ProcessingSettings
from services.processing_service import ProcessingService


def test_report_failure_is_partial_success_and_preserves_copy(tmp_path, monkeypatch) -> None:
    excel = tmp_path / "input.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    sheet.append(["ID"])
    sheet.append(["100"])
    workbook.save(excel)
    source = tmp_path / "source"
    source.mkdir()
    (source / "100.jpg").write_bytes(b"image")
    destination = tmp_path / "destination"
    settings = ProcessingSettings(
        excel,
        "Data",
        ColumnInfo(1, "ID", "A"),
        source,
        destination,
        generate_report=True,
        generate_manifest=False,
    )
    service = ProcessingService()

    def fail_report(_result):
        raise OSError("simulated report failure")

    monkeypatch.setattr(service.reporter, "create", fail_report)
    result = service.run(settings, False, logging.getLogger("report-failure"))
    assert result.outcome == "partial"
    assert result.stats.copied_files == 1
    assert (destination / "100.jpg").exists()
    assert "simulated report failure" in result.report_error
