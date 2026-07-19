"""اختبار تكامل المعاينة واكتشاف التكرار والتطابقات المتعددة."""

import logging

from openpyxl import Workbook

from models.result_models import ColumnInfo, MultipleMatchPolicy, ProcessingSettings
from services.processing_service import ProcessingService


def test_preview_counts_duplicates_missing_and_multiple(tmp_path) -> None:
    excel = tmp_path / "input.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "الأفراد"
    sheet.append(["الرقم الذاتي"])
    for value in ["one", "ONE", "two", "missing", None]:
        sheet.append([value])
    workbook.save(excel)
    source = tmp_path / "images"
    source.mkdir()
    (source / "one.jpg").write_bytes(b"1")
    (source / "two.jpg").write_bytes(b"2")
    (source / "two.png").write_bytes(b"2")
    destination = tmp_path / "out"
    settings = ProcessingSettings(
        excel,
        "الأفراد",
        ColumnInfo(1, "الرقم الذاتي", "A", 1),
        source,
        destination,
        multiple_match_policy=MultipleMatchPolicy.ALL,
    )
    logger = logging.getLogger("test_processing")
    result = ProcessingService().run(settings, True, logger)
    assert result.stats.total_excel_rows == 5
    assert result.stats.valid_identifiers == 4
    assert result.stats.duplicate_identifiers == 1
    assert result.stats.matched_identifiers == 2
    assert result.stats.unmatched_identifiers == 1
    assert result.stats.multiple_match_identifiers == 1
    assert len([record for record in result.records if record.identifier == "two"]) == 2
    assert not destination.exists()
