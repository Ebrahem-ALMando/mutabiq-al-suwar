"""اختبارات استيراد CSV/TSV العربي واكتشاف العمود."""

from services.excel_service import ExcelService, detect_delimited_format


def test_utf8_csv_import_and_column_scoring(tmp_path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("الاسم,الرقم الوظيفي\nأحمد,000125\nسارة,A-77\n", encoding="utf-8-sig")
    service = ExcelService()
    info = service.workbook_info(path)
    columns = service.columns(path, info.active_worksheet)
    scores = service.score_columns(path, info.active_worksheet, columns)
    assert scores[0].column.header == "الرقم الوظيفي"
    records = service.read_identifiers(path, info.active_worksheet, scores[0].column)
    assert [record.identifier for record in records] == ["000125", "A-77"]


def test_cp1256_semicolon_csv_and_tsv_detection(tmp_path) -> None:
    csv_path = tmp_path / "arabic.csv"
    csv_path.write_bytes("الرقم;الاسم\n123;علي\n".encode("cp1256"))
    assert detect_delimited_format(csv_path).delimiter == ";"
    tsv_path = tmp_path / "data.tsv"
    tsv_path.write_text("ID\tName\n1\tA\n", encoding="utf-8")
    assert detect_delimited_format(tsv_path).delimiter == "\t"
