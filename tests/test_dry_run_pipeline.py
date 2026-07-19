"""اختبار المحاكاة الكاملة والسجل والمنشور دون نسخ."""

import logging

from openpyxl import Workbook

from models.result_models import ColumnInfo, ProcessingSettings
from repositories.history_repository import HistoryRepository
from services.manifest_service import ManifestService
from services.processing_service import ProcessingService


def test_complete_dry_run_creates_manifest_history_but_no_image(tmp_path) -> None:
    excel = tmp_path / "data.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["الرقم الذاتي"])
    sheet.append(["A1"])
    workbook.save(excel)
    source = tmp_path / "images"
    source.mkdir()
    (source / "A1.jpg").write_bytes(b"image")
    destination = tmp_path / "out"
    settings = ProcessingSettings(
        excel, sheet.title, ColumnInfo(1, "الرقم الذاتي", "A"), source, destination, dry_run=True, generate_report=False
    )
    history = HistoryRepository(tmp_path / "app.db")
    manifests = ManifestService(tmp_path / "manifests")
    result = ProcessingService(history, manifests).run(settings, False, logging.getLogger("dry-run"))
    assert result.stats.matched_identifiers == 1
    assert result.stats.copied_files == 0
    assert not (destination / "A1.jpg").exists()
    assert result.manifest_path.exists()
    assert history.batch(result.batch_id)["dry_run"] == 1
