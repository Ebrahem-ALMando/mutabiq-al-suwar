"""قياس اصطناعي قابل للتكرار للقراءة والمطابقة والنسخ."""

from __future__ import annotations

import json
import logging
import tempfile
import time
from pathlib import Path

import psutil

from models.result_models import ColumnInfo, ProcessingSettings
from services.copy_service import CopyService
from services.excel_service import ExcelService
from services.matching_service import SmartMatchingEngine


def main() -> None:
    process = psutil.Process()
    baseline_memory = process.memory_info().rss
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        csv_path = root / "large.csv"
        row_count = 100_000
        with csv_path.open("w", encoding="utf-8", newline="") as stream:
            stream.write("ID\n")
            for number in range(row_count):
                stream.write(f"ID{number:06}\n")
        service = ExcelService()
        started = time.perf_counter()
        records = service.read_identifiers(csv_path, "البيانات", ColumnInfo(1, "ID", "A"))
        read_seconds = time.perf_counter() - started
        settings = ProcessingSettings(csv_path, "البيانات", ColumnInfo(1, "ID", "A"), root, root / "out")
        engine = SmartMatchingEngine()
        started = time.perf_counter()
        index = {f"id{number:06}": [Path(f"ID{number:06}.jpg")] for number in range(row_count)}
        index_seconds = time.perf_counter() - started
        started = time.perf_counter()
        matched = sum(engine.identifier_key(record.identifier, settings) in index for record in records)
        match_seconds = time.perf_counter() - started
        copy_source = root / "copy-source"
        copy_source.mkdir()
        file_count = 64
        file_size = 256 * 1024
        payload = b"x" * file_size
        for number in range(file_count):
            (copy_source / f"file-{number:03}.jpg").write_bytes(payload)
        copy_destination = root / "copy-out"
        started = time.perf_counter()
        for source in copy_source.iterdir():
            CopyService().copy_verified(source, copy_destination, settings.duplicate_policy)
        copy_seconds = time.perf_counter() - started
        copied_bytes = file_count * file_size
        peak_delta = max(0, process.memory_info().rss - baseline_memory)
        print(json.dumps({
            "rows": len(records), "simulated_index_paths": len(index), "matched": matched,
            "csv_read_seconds": round(read_seconds, 4), "index_build_seconds": round(index_seconds, 4),
            "matching_seconds": round(match_seconds, 4), "copied_files": file_count,
            "copied_bytes": copied_bytes, "copy_seconds": round(copy_seconds, 4),
            "copy_mib_per_second": round(copied_bytes / 1024 / 1024 / copy_seconds, 2),
            "rss_delta_mib": round(peak_delta / 1024 / 1024, 2),
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    main()

