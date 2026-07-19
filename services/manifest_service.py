"""إنشاء وقراءة منشور عملية JSON قابل للتدقيق."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from models.result_models import JobResult
from utils.version import APP_VERSION, MANIFEST_SCHEMA_VERSION


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """احسب SHA-256 بذاكرة ثابتة."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: json_safe(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    return value


class ManifestService:
    """يكتب منشوراً جديداً حصراً ولا يستبدل منشوراً سابقاً."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)

    def create(self, result: JobResult) -> Path:
        payload = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "application_version": APP_VERSION,
            "batch_id": result.batch_id,
            "batch_name": result.settings.batch_name or result.settings.excel_path.stem,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "dry_run": result.settings.dry_run,
            "outcome": result.outcome,
            "inputs": {
                "data_file": str(result.settings.excel_path),
                "worksheet": result.settings.worksheet,
                "source_folder": str(result.settings.source_folder),
                "destination_folder": str(result.settings.destination_folder),
            },
            "settings": json_safe(result.settings),
            "statistics": json_safe(result.stats),
            "preflight": json_safe(result.preflight_checks),
            "records": [json_safe(record) for record in result.records],
            "report_path": str(result.report_path or ""),
            "log_path": str(result.log_path or ""),
        }
        path = self.directory / f"batch_{result.batch_id}.json"
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return path

    @staticmethod
    def load(path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema_version") != MANIFEST_SCHEMA_VERSION:
            raise ValueError("منشور العملية غير صالح أو غير مدعوم.")
        return data
