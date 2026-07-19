"""تراجع محكوم بمنشور العملية ولا يمس الملفات السابقة أو المعدلة."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from repositories.history_repository import HistoryRepository
from services.manifest_service import ManifestService, file_sha256
from utils.path_helpers import is_path_within


@dataclass(frozen=True, slots=True)
class UndoCandidate:
    path: Path
    safe: bool
    reason: str


@dataclass(slots=True)
class UndoResult:
    batch_id: str
    removed: list[Path]
    skipped: list[UndoCandidate]
    report_path: Path

    @property
    def status(self) -> str:
        if self.removed and not self.skipped:
            return "fully_undone"
        if self.removed:
            return "partially_undone"
        return "undo_failed"


class UndoService:
    """يفحص metadata/hash قبل أي حذف ويحتاج تأكيداً صريحاً للتنفيذ."""

    def __init__(self, history: HistoryRepository) -> None:
        self.history = history

    def plan(self, manifest_path: Path) -> tuple[dict, list[UndoCandidate]]:
        manifest = ManifestService.load(manifest_path)
        if manifest.get("dry_run"):
            raise ValueError("لا يمكن التراجع عن عملية محاكاة لم تنسخ ملفات.")
        destination_root = Path(manifest["inputs"]["destination_folder"])
        candidates: list[UndoCandidate] = []
        for record in manifest.get("records", []):
            if record.get("copy_status") not in {"copied", "renamed"} or not record.get("created_new_file"):
                continue
            path = Path(record.get("destination_path", ""))
            if not path or not is_path_within(path, destination_root):
                candidates.append(UndoCandidate(path, False, "المسار خارج مجلد الوجهة المسجل."))
                continue
            if not path.is_file():
                candidates.append(UndoCandidate(path, False, "الملف لم يعد موجوداً."))
                continue
            stat = path.stat()
            if stat.st_size != int(record.get("destination_size", -1)):
                candidates.append(UndoCandidate(path, False, "تغير حجم الملف بعد النسخ."))
                continue
            if stat.st_mtime_ns != int(record.get("destination_mtime_ns", -1)):
                candidates.append(UndoCandidate(path, False, "تاريخ تعديل الملف تغير بعد النسخ."))
                continue
            expected_hash = record.get("destination_sha256", "")
            if expected_hash and file_sha256(path) != expected_hash:
                candidates.append(UndoCandidate(path, False, "تغير محتوى الملف بعد النسخ."))
                continue
            candidates.append(UndoCandidate(path, True, "يطابق بيانات المنشور ولم يتغير."))
        return manifest, candidates

    def execute(self, manifest_path: Path, confirmed: bool) -> UndoResult:
        if not confirmed:
            raise PermissionError("يتطلب التراجع تأكيداً صريحاً.")
        manifest, candidates = self.plan(manifest_path)
        removed: list[Path] = []
        skipped: list[UndoCandidate] = []
        for candidate in candidates:
            if not candidate.safe:
                skipped.append(candidate)
                continue
            try:
                candidate.path.unlink()
                removed.append(candidate.path)
            except OSError as exc:
                skipped.append(UndoCandidate(candidate.path, False, f"تعذر الحذف: {exc}"))
        report = {
            "batch_id": manifest["batch_id"],
            "undo_time": datetime.now(UTC).isoformat(),
            "removed": [str(path) for path in removed],
            "skipped": [{"path": str(item.path), "reason": item.reason} for item in skipped],
        }
        report_path = manifest_path.with_name(f"undo_{manifest['batch_id']}.json")
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        result = UndoResult(manifest["batch_id"], removed, skipped, report_path)
        self.history.mark_undo(result.batch_id, result.status)
        return result
