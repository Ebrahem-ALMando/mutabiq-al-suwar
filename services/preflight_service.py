"""قائمة فحص قبلي حقيقية قبل النسخ."""

from __future__ import annotations

import os
import shutil
import sqlite3
import uuid
from pathlib import Path

from models.result_models import JobResult, PreflightCheck, PreflightLevel, ProcessingSettings
from services.destination_service import validate_template
from utils.path_helpers import is_path_within


class PreflightService:
    """يتحقق من المدخلات والمساحة والتعارض والكتابة من دون نسخ صور."""

    def run(
        self,
        settings: ProcessingSettings,
        preview: JobResult | None = None,
        database_path: Path | None = None,
        create_destination: bool = False,
    ) -> list[PreflightCheck]:
        checks: list[PreflightCheck] = []
        self._add(
            checks,
            settings.excel_path.is_file(),
            "DATA_READ",
            "ملف البيانات",
            "يمكن الوصول إلى ملف البيانات.",
            "ملف البيانات غير موجود أو غير قابل للوصول.",
        )
        self._add(
            checks,
            bool(settings.worksheet and settings.column.index > 0),
            "COLUMN",
            "عمود المعرّف",
            "تم تحديد ورقة وعمود صالحين.",
            "حدد ورقة العمل وعمود المعرّف.",
        )
        self._add(
            checks,
            settings.source_folder.is_dir(),
            "SOURCE",
            "مجلد الصور",
            "مجلد المصدر متاح.",
            "مجلد الصور غير موجود.",
        )
        same = False
        try:
            same = (
                settings.source_folder.exists()
                and settings.destination_folder.exists()
                and os.path.samefile(settings.source_folder, settings.destination_folder)
            )
        except OSError:
            same = settings.source_folder.resolve() == settings.destination_folder.resolve()
        self._add(
            checks,
            not same,
            "SAME_FOLDER",
            "فصل المصدر والوجهة",
            "المصدر والوجهة مختلفان.",
            "المصدر والوجهة يشيران إلى المجلد نفسه.",
        )
        if is_path_within(settings.destination_folder, settings.source_folder):
            checks.append(
                PreflightCheck(
                    "NESTED_DEST",
                    "الوجهة داخل المصدر",
                    PreflightLevel.WARNING,
                    "سيتم استبعاد الوجهة من الفهرسة لمنع إعادة قراءة النتائج.",
                    "يفضل استخدام وجهة خارج المصدر.",
                )
            )
        try:
            write_folder = settings.destination_folder
            if not write_folder.exists():
                if create_destination:
                    write_folder.mkdir(parents=True, exist_ok=True)
                else:
                    write_folder = next(
                        (parent for parent in settings.destination_folder.parents if parent.exists()),
                        settings.destination_folder.parent,
                    )
            marker = write_folder / f".mutabiq-write-{uuid.uuid4().hex}.tmp"
            marker.write_bytes(b"write-test")
            marker.unlink()
            checks.append(
                PreflightCheck("DEST_WRITE", "صلاحية الكتابة", PreflightLevel.PASSED, "يمكن الكتابة في الوجهة.")
            )
        except OSError as exc:
            checks.append(
                PreflightCheck(
                    "DEST_WRITE",
                    "صلاحية الكتابة",
                    PreflightLevel.FAILED,
                    f"تعذرت الكتابة في الوجهة: {exc}",
                    "اختر مجلداً تملك صلاحية الكتابة فيه.",
                )
            )
        required = 0
        if preview:
            unique_sources = {record.source_path for record in preview.records if record.source_path}
            for source in unique_sources:
                try:
                    required += source.stat().st_size
                except OSError:
                    continue
            preview.stats.estimated_copy_bytes = required
        try:
            disk_target = (
                settings.destination_folder
                if settings.destination_folder.exists()
                else next(
                    (parent for parent in settings.destination_folder.parents if parent.exists()),
                    settings.destination_folder.parent,
                )
            )
            free = shutil.disk_usage(disk_target).free
            margin = max(50 * 1024 * 1024, int(required * 0.1))
            level = (
                PreflightLevel.FAILED
                if required and free < required
                else PreflightLevel.WARNING if required and free < required + margin else PreflightLevel.PASSED
            )
            checks.append(
                PreflightCheck(
                    "DISK_SPACE",
                    "مساحة القرص",
                    level,
                    f"المطلوب تقريباً {required:,} بايت؛ المتاح {free:,} بايت.",
                    "حرر مساحة إضافية أو اختر قرصاً آخر." if level != PreflightLevel.PASSED else "",
                )
            )
        except OSError:
            checks.append(
                PreflightCheck(
                    "DISK_SPACE",
                    "مساحة القرص",
                    PreflightLevel.WARNING,
                    "تعذر تحديد المساحة المتاحة، وهو شائع في بعض مشاركات الشبكة.",
                )
            )
        conflicts = 0
        long_paths = 0
        if preview:
            for record in preview.records:
                if not record.source_path:
                    continue
                target = settings.destination_folder / (record.destination_filename_override or record.source_path.name)
                conflicts += int(target.exists())
                long_paths += int(len(str(target.resolve())) >= 240)
        checks.append(
            PreflightCheck(
                "CONFLICTS",
                "تعارضات الوجهة",
                PreflightLevel.WARNING if conflicts else PreflightLevel.PASSED,
                f"عدد الملفات الموجودة مسبقاً: {conflicts}.",
            )
        )
        checks.append(
            PreflightCheck(
                "LONG_PATHS",
                "طول المسارات",
                PreflightLevel.WARNING if long_paths else PreflightLevel.PASSED,
                f"مسارات قد تتجاوز حد التوافق التقليدي: {long_paths}.",
            )
        )
        template_errors = (
            validate_template(settings.destination_folder_template) if settings.destination_folder_template else []
        )
        template_errors += (
            validate_template(settings.destination_filename_template) if settings.destination_filename_template else []
        )
        checks.append(
            PreflightCheck(
                "TEMPLATES",
                "قوالب الوجهة",
                PreflightLevel.FAILED if template_errors else PreflightLevel.PASSED,
                " ".join(template_errors) or "القوالب صالحة.",
            )
        )
        rules = [rule for rule in settings.transformation_rules if rule.enabled]
        checks.append(
            PreflightCheck(
                "RULES",
                "قواعد المطابقة",
                PreflightLevel.PASSED,
                f"النمط: {settings.matching_mode.value}؛ القواعد الفعالة: {len(rules)}.",
            )
        )
        if database_path:
            try:
                with sqlite3.connect(database_path) as connection:
                    connection.execute("SELECT 1")
                checks.append(
                    PreflightCheck("SQLITE", "قاعدة البيانات", PreflightLevel.PASSED, "قاعدة السجل المحلي متاحة.")
                )
            except sqlite3.Error as exc:
                checks.append(
                    PreflightCheck("SQLITE", "قاعدة البيانات", PreflightLevel.FAILED, f"تعذر فتح SQLite: {exc}")
                )
        return checks

    @staticmethod
    def _add(checks: list[PreflightCheck], condition: bool, code: str, title: str, passed: str, failed: str) -> None:
        checks.append(
            PreflightCheck(
                code,
                title,
                PreflightLevel.PASSED if condition else PreflightLevel.FAILED,
                passed if condition else failed,
            )
        )

    @staticmethod
    def has_fatal(checks: list[PreflightCheck]) -> bool:
        return any(check.level == PreflightLevel.FAILED for check in checks)
