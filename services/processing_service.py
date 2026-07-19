"""خط المعالجة الكامل للمعاينة والنسخ مع دعم الإلغاء."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from models.result_models import (
    CopyStatus,
    JobResult,
    MatchStatus,
    MultipleMatchPolicy,
    PreflightLevel,
    ProcessingSettings,
    ProcessingStats,
    ResultRecord,
)
from repositories.history_repository import HistoryRepository
from services.copy_service import CopyService
from services.destination_service import render_template, sanitize_component
from services.excel_service import ExcelService
from services.image_matcher import ImageMatcher
from services.manifest_service import ManifestService
from services.matching_service import SmartMatchingEngine
from services.preflight_service import PreflightService
from services.report_service import ReportService
from utils.path_helpers import is_path_within

EventCallback = Callable[[str, int, int, str, ProcessingStats], None]
CancelCallback = Callable[[], bool]
PauseCallback = Callable[[], None]


class ProcessingService:
    """ينسّق القراءة والفهرسة والمطابقة والنسخ والتقرير."""

    def __init__(
        self,
        history: HistoryRepository | None = None,
        manifest_service: ManifestService | None = None,
    ) -> None:
        self.excel = ExcelService()
        self.matcher = ImageMatcher()
        self.copier = CopyService()
        self.reporter = ReportService()
        self.smart_matcher = SmartMatchingEngine()
        self.preflight = PreflightService()
        self.history = history
        self.manifests = manifest_service

    def run(
        self,
        settings: ProcessingSettings,
        preview_only: bool,
        logger: logging.Logger,
        event: EventCallback | None = None,
        cancelled: CancelCallback | None = None,
        wait_if_paused: PauseCallback | None = None,
        overrides: JobResult | None = None,
    ) -> JobResult:
        """نفّذ المهمة كاملة؛ ولا ينسخ شيئاً عند طلب المعاينة."""

        started = time.monotonic()
        stats = ProcessingStats()
        result = JobResult(settings=settings, stats=stats)
        if logger.handlers and hasattr(logger.handlers[0], "baseFilename"):
            result.log_path = Path(logger.handlers[0].baseFilename)

        def emit(stage: str, current: int, total: int, item: str = "") -> None:
            stats.elapsed_seconds = time.monotonic() - started
            if event:
                event(stage, current, total, item, stats)

        def is_cancelled() -> bool:
            return bool(cancelled and cancelled())

        logger.info("بدء %s", "المعاينة" if preview_only else "المعالجة")
        logger.info("الإعدادات: %s", settings)
        emit("قراءة ملف Excel", 0, 0, settings.excel_path.name)
        identifiers = self.excel.read_identifiers(
            settings.excel_path,
            settings.worksheet,
            settings.column,
            settings.trim_identifiers,
            settings.case_insensitive,
            settings.start_row,
            settings.end_row,
            settings.secondary_column,
        )
        stats.total_excel_rows = len(identifiers)
        stats.empty_values = sum(record.is_empty for record in identifiers)
        stats.valid_identifiers = stats.total_excel_rows - stats.empty_values
        stats.duplicate_identifiers = sum(record.is_duplicate for record in identifiers)
        stats.unique_identifiers = stats.valid_identifiers - stats.duplicate_identifiers
        emit("قراءة ملف Excel", len(identifiers), len(identifiers))
        if stats.valid_identifiers == 0:
            raise ValueError("العمود المحدد لا يحتوي على قيم صالحة.")
        if is_cancelled():
            result.cancelled = True
            return result

        emit("فهرسة الصور", 0, 0, settings.source_folder.name)
        excluded = (
            settings.destination_folder
            if settings.recursive and is_path_within(settings.destination_folder, settings.source_folder)
            else None
        )

        def key_transform(stem: str) -> str:
            return self.smart_matcher.stem_key(stem, settings)

        if self.history and settings.use_persistent_index:
            index, scanned = self.history.refresh_image_index(
                settings.source_folder,
                settings.recursive,
                key_transform,
                excluded=excluded,
                progress=lambda current, total, item: emit("فهرسة الصور", current, total, item),
                cancelled=is_cancelled,
            )
        else:
            index, scanned = self.matcher.scan(
                settings.source_folder,
                settings.recursive,
                settings.case_insensitive,
                excluded_folder=excluded,
                progress=lambda current, total, item: emit("فهرسة الصور", current, total, item),
                cancelled=is_cancelled,
                key_transform=key_transform,
            )
        stats.source_images_scanned = scanned
        logger.info("تم فهرسة %d ملف صورة ضمن %d مفتاح", scanned, len(index))
        if is_cancelled():
            result.cancelled = True
            return result
        if scanned == 0:
            raise ValueError("لم يُعثر على ملفات صور ذات امتدادات مدعومة في مجلد المصدر.")

        emit("مطابقة الأرقام", 0, len(identifiers))
        sequence = 0
        matched_keys: set[str] = set()
        unmatched_keys: set[str] = set()
        multiple_keys: set[str] = set()
        for current, identifier_record in enumerate(identifiers, start=1):
            if is_cancelled():
                result.cancelled = True
                break
            if wait_if_paused:
                wait_if_paused()
            sequence += 1
            original = "" if identifier_record.original_value is None else str(identifier_record.original_value)
            if identifier_record.is_empty:
                result.records.append(
                    ResultRecord(
                        sequence,
                        identifier_record.row_number,
                        original,
                        "",
                        MatchStatus.EMPTY,
                        notes="تم تجاهل خلية فارغة.",
                        secondary_name=identifier_record.secondary_name,
                    )
                )
                emit("مطابقة الأرقام", current, len(identifiers), "")
                continue
            if identifier_record.is_duplicate and settings.ignore_duplicate_identifiers:
                result.records.append(
                    ResultRecord(
                        sequence,
                        identifier_record.row_number,
                        original,
                        identifier_record.identifier,
                        MatchStatus.DUPLICATE,
                        notes="تم تجاهل القيمة المكررة وفق الإعداد المحدد.",
                        secondary_name=identifier_record.secondary_name,
                    )
                )
                emit("مطابقة الأرقام", current, len(identifiers), identifier_record.identifier)
                continue
            logical_key = self.smart_matcher.identifier_key(identifier_record.identifier, settings)
            matches = list(index.get(logical_key, []))
            if not matches:
                unmatched_keys.add(logical_key)
                suggestions = (
                    self.smart_matcher.suggestions(index, identifier_record.identifier, settings)
                    if settings.matching_mode.value == "fuzzy"
                    else []
                )
                if suggestions:
                    best = suggestions[0]
                    result.records.append(
                        ResultRecord(
                            sequence,
                            identifier_record.row_number,
                            original,
                            identifier_record.identifier,
                            MatchStatus.FUZZY,
                            notes="اقتراح فقط؛ يحتاج موافقة صريحة قبل النسخ.",
                            secondary_name=identifier_record.secondary_name,
                            similarity_score=best.score,
                            match_explanation=best.explanation,
                            candidate_paths=[path for suggestion in suggestions for path in suggestion.paths],
                            selected_for_copy=False,
                        )
                    )
                else:
                    result.records.append(
                        ResultRecord(
                            sequence,
                            identifier_record.row_number,
                            original,
                            identifier_record.identifier,
                            MatchStatus.NOT_FOUND,
                            notes="لم توجد صورة بساق اسم مطابقة تماماً.",
                            secondary_name=identifier_record.secondary_name,
                        )
                    )
                logger.warning("لا يوجد تطابق لصف Excel رقم %d", identifier_record.row_number)
            else:
                matched_keys.add(logical_key)
                status = MatchStatus.MATCHED
                selected = matches[:1]
                note = ""
                if len(matches) > 1:
                    status = MatchStatus.MULTIPLE
                    multiple_keys.add(logical_key)
                    note = f"وُجد {len(matches)} تطابقات."
                    if settings.multiple_match_policy == MultipleMatchPolicy.ALL:
                        selected = matches
                    else:
                        note += " تم اختيار أول تطابق حسب الترتيب المحدد."
                for match_index, source_path in enumerate(selected):
                    result.records.append(
                        ResultRecord(
                            sequence,
                            identifier_record.row_number,
                            original,
                            identifier_record.identifier,
                            status,
                            source_path=source_path,
                            notes=note,
                            secondary_name=identifier_record.secondary_name,
                            candidate_paths=matches,
                            source_size=source_path.stat().st_size if source_path.exists() else 0,
                        )
                    )
                    if match_index < len(selected) - 1:
                        sequence += 1
                logger.info("صف Excel رقم %d: %d تطابق", identifier_record.row_number, len(matches))
            emit("مطابقة الأرقام", current, len(identifiers), identifier_record.identifier)
        stats.matched_identifiers = len(matched_keys)
        stats.unmatched_identifiers = len(unmatched_keys)
        stats.multiple_match_identifiers = len(multiple_keys)

        if overrides:
            self._apply_overrides(result, overrides)

        result.preflight_checks = self.preflight.run(
            settings,
            result,
            self.history.database_path if self.history else None,
            create_destination=not preview_only,
        )
        if not preview_only and self.preflight.has_fatal(result.preflight_checks):
            failures = [check.detail for check in result.preflight_checks if check.level == PreflightLevel.FAILED]
            raise ValueError("فشل الفحص القبلي: " + " ".join(failures))

        if not preview_only and not result.cancelled:
            copy_records = [record for record in result.records if record.source_path and record.selected_for_copy]
            emit("نسخ الصور", 0, len(copy_records))
            for current, record in enumerate(copy_records, start=1):
                if is_cancelled():
                    result.cancelled = True
                    record.copy_status = CopyStatus.CANCELLED
                    break
                if wait_if_paused:
                    wait_if_paused()
                try:
                    assert record.source_path is not None
                    destination_folder, destination_name = self._destination_for(record, settings)
                    if settings.dry_run:
                        destination = destination_folder / destination_name
                        record.destination_path = destination
                        record.notes = "; ".join(filter(None, [record.notes, "محاكاة فقط؛ لم يُنسخ الملف."]))
                        emit("محاكاة النسخ", current, len(copy_records), record.source_filename)
                        continue
                    outcome = self.copier.copy_verified(
                        record.source_path,
                        destination_folder,
                        settings.duplicate_policy,
                        destination_name=destination_name,
                        verify_hash=settings.verify_hash,
                        retries=settings.retry_count,
                        retry_delay=settings.retry_delay_seconds,
                    )
                    record.copy_status = outcome.status
                    record.destination_path = outcome.target
                    record.source_size = outcome.source_size
                    record.destination_size = outcome.destination_size
                    record.destination_mtime_ns = outcome.destination_mtime_ns
                    record.destination_sha256 = outcome.destination_sha256
                    record.created_new_file = outcome.created_new_file
                    record.verified = outcome.verified
                    record.notes = "; ".join(filter(None, [record.notes, outcome.note]))
                    if outcome.status == CopyStatus.COPIED:
                        stats.copied_files += 1
                        stats.copied_bytes += outcome.destination_size
                    elif outcome.status == CopyStatus.RENAMED:
                        stats.copied_files += 1
                        stats.renamed_files += 1
                        stats.copied_bytes += outcome.destination_size
                    elif outcome.status == CopyStatus.SKIPPED:
                        stats.skipped_files += 1
                    logger.info("نسخ صف %d (%s)", record.excel_row, outcome.status.value)
                except Exception as exc:
                    stats.failed_copies += 1
                    record.copy_status = CopyStatus.FAILED
                    record.notes = f"تعذر نسخ الملف: {exc}"
                    logger.exception("فشل نسخ %s", record.source_path)
                emit("نسخ الصور", current, len(copy_records), record.source_filename)

            if settings.generate_report and not result.cancelled:
                emit("إنشاء التقرير", 0, 1)
                try:
                    result.report_path = self.reporter.create(result)
                    logger.info("تم إنشاء التقرير: %s", result.report_path)
                except Exception as exc:
                    logger.exception("فشل إنشاء التقرير")
                    raise RuntimeError("تعذر إنشاء تقرير Excel. راجع ملف السجل للتفاصيل.") from exc
                emit("إنشاء التقرير", 1, 1, result.report_path.name)

        stats.elapsed_seconds = time.monotonic() - started
        result.finished_at = datetime.now(UTC).isoformat()
        if not preview_only:
            if settings.generate_manifest and self.manifests:
                result.manifest_path = self.manifests.create(result)
                logger.info("تم إنشاء منشور العملية: %s", result.manifest_path)
            if self.history:
                self.history.record_result(result)
        emit("تم إكمال العملية" if not result.cancelled else "تم إلغاء العملية", 1, 1)
        logger.info("النتيجة النهائية: %s", stats.as_dict())
        return result

    @staticmethod
    def _destination_for(record: ResultRecord, settings: ProcessingSettings) -> tuple[Path, str]:
        """حل مجلد واسم الوجهة من القوالب الآمنة."""

        assert record.source_path is not None
        values = {
            "identifier": record.identifier,
            "name": record.secondary_name,
            "excel_name": settings.excel_path.stem,
            "worksheet": settings.worksheet,
            "sequence": record.sequence,
        }
        folder = settings.destination_folder
        if settings.destination_folder_template:
            folder = folder / render_template(settings.destination_folder_template, values, record.source_path.suffix)
        if record.destination_filename_override:
            name = sanitize_component(record.destination_filename_override)
        elif settings.destination_filename_template:
            name = render_template(settings.destination_filename_template, values, record.source_path.suffix)
            if not Path(name).suffix:
                name += record.source_path.suffix
            name = sanitize_component(name)
        else:
            name = record.source_path.name
        return folder, name

    @staticmethod
    def _apply_overrides(result: JobResult, preview: JobResult) -> None:
        """أعد تطبيق القرارات اليدوية على نتيجة إعادة الفحص قبل النسخ."""

        manual = {
            (record.excel_row, record.identifier): record
            for record in preview.records
            if record.manually_modified or not record.selected_for_copy or record.destination_filename_override
        }
        for record in result.records:
            override = manual.get((record.excel_row, record.identifier))
            if not override:
                continue
            record.source_path = override.source_path
            record.selected_for_copy = override.selected_for_copy
            record.destination_filename_override = override.destination_filename_override
            record.notes = override.notes
            record.reviewed = override.reviewed
            record.manually_modified = True
            record.match_status = override.match_status
