"""نسخ الصور مع سياسات تعارض آمنة وقابلة للاختبار."""

from __future__ import annotations

import os
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from models.result_models import CopyStatus, DuplicatePolicy
from services.manifest_service import file_sha256
from utils.path_helpers import unique_destination


@dataclass(frozen=True, slots=True)
class CopyOutcome:
    """نتيجة نسخ موثقة بما يكفي للمنشور والتراجع الآمن."""

    status: CopyStatus
    target: Path
    note: str
    source_size: int
    destination_size: int
    destination_mtime_ns: int
    destination_sha256: str
    verified: bool
    created_new_file: bool


class CopyService:
    """ينفّذ نسخ ملف واحد ويحافظ على بياناته الوصفية المتاحة."""

    def copy(self, source: Path, destination_folder: Path, policy: DuplicatePolicy) -> tuple[CopyStatus, Path, str]:
        """انسخ ملفاً وفق سياسة التعارض وأعد الحالة والمسار والملاحظة."""

        outcome = self.copy_verified(source, destination_folder, policy)
        return outcome.status, outcome.target, outcome.note

    def copy_verified(
        self,
        source: Path,
        destination_folder: Path,
        policy: DuplicatePolicy,
        *,
        destination_name: str = "",
        verify_hash: bool = False,
        retries: int = 0,
        retry_delay: float = 0.5,
    ) -> CopyOutcome:
        """انسخ إلى ملف مؤقت، flush، تحقق، ثم أعد التسمية ذرياً مع retries محدودة."""

        last_error: OSError | None = None
        for attempt in range(max(0, retries) + 1):
            try:
                return self._copy_once(source, destination_folder, policy, destination_name, verify_hash)
            except OSError as exc:
                last_error = exc
                if attempt >= retries:
                    raise
                time.sleep(max(0.0, retry_delay))
        raise last_error or OSError("تعذر نسخ الملف.")

    def _copy_once(
        self,
        source: Path,
        destination_folder: Path,
        policy: DuplicatePolicy,
        destination_name: str,
        verify_hash: bool,
    ) -> CopyOutcome:
        if not source.is_file():
            raise FileNotFoundError(source)
        destination_folder.mkdir(parents=True, exist_ok=True)
        target = destination_folder / (destination_name or source.name)
        renamed = False
        if target.exists():
            if policy == DuplicatePolicy.SKIP:
                stat = target.stat()
                return CopyOutcome(
                    CopyStatus.SKIPPED,
                    target,
                    "الملف موجود مسبقاً.",
                    source.stat().st_size,
                    stat.st_size,
                    stat.st_mtime_ns,
                    "",
                    True,
                    False,
                )
            if policy == DuplicatePolicy.RENAME:
                target = unique_destination(target)
                renamed = True

        existed_before = target.exists()

        temp_target = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        try:
            source_size = source.stat().st_size
            with source.open("rb") as source_stream, temp_target.open("xb") as destination_stream:
                shutil.copyfileobj(source_stream, destination_stream, length=1024 * 1024)
                destination_stream.flush()
                os.fsync(destination_stream.fileno())
            shutil.copystat(source, temp_target)
            temp_size = temp_target.stat().st_size
            if temp_size != source_size:
                raise OSError(f"فشل تحقق الحجم: المصدر {source_size} والمؤقت {temp_size}.")
            digest = ""
            if verify_hash:
                source_hash = file_sha256(source)
                digest = file_sha256(temp_target)
                if digest != source_hash:
                    raise OSError("فشل تحقق SHA-256 للملف المؤقت.")
            os.replace(temp_target, target)
        except Exception:
            try:
                temp_target.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        status = CopyStatus.RENAMED if renamed else CopyStatus.COPIED
        note = "تم إنشاء اسم جديد تلقائياً." if renamed else "تم النسخ بنجاح."
        stat = target.stat()
        return CopyOutcome(
            status,
            target,
            note + " تم التحقق من الحجم." + (" وتم التحقق من SHA-256." if verify_hash else ""),
            source_size,
            stat.st_size,
            stat.st_mtime_ns,
            digest,
            stat.st_size == source_size,
            not existed_before,
        )
