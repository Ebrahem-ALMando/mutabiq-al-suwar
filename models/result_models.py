"""نماذج وعدادات نتائج معالجة الصور."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class DuplicatePolicy(StrEnum):
    """طريقة التعامل مع ملف موجود مسبقاً في الوجهة."""

    SKIP = "skip"
    OVERWRITE = "overwrite"
    RENAME = "rename"


class MultipleMatchPolicy(StrEnum):
    """طريقة التعامل مع أكثر من صورة للمعرّف نفسه."""

    FIRST = "first"
    ALL = "all"


class MatchingMode(StrEnum):
    """أنماط المطابقة المتاحة، مع بقاء الدقيقة هي الافتراضية."""

    EXACT = "exact"
    NORMALIZED = "normalized"
    PATTERN = "pattern"
    FUZZY = "fuzzy"


class PreflightLevel(StrEnum):
    """شدة نتيجة فحص قبلي."""

    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


class MatchStatus(StrEnum):
    """حالة مطابقة معرّف Excel."""

    MATCHED = "matched"
    NOT_FOUND = "not_found"
    MULTIPLE = "multiple"
    DUPLICATE = "duplicate"
    EMPTY = "empty"
    ERROR = "error"
    FUZZY = "fuzzy"
    MANUAL = "manual"


class CopyStatus(StrEnum):
    """حالة عملية النسخ."""

    NOT_REQUESTED = "not_requested"
    COPIED = "copied"
    SKIPPED = "skipped"
    RENAMED = "renamed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class ColumnInfo:
    """وصف عمود قابل للاختيار من ورقة عمل."""

    index: int
    header: str
    letter: str
    header_row: int = 1

    @property
    def display_name(self) -> str:
        return f"{self.header} ({self.letter})"


@dataclass(slots=True)
class IdentifierRecord:
    """قيمة مستخرجة من خلية Excel مع معلوماتها الأصلية."""

    row_number: int
    original_value: Any
    identifier: str
    is_empty: bool = False
    is_duplicate: bool = False
    secondary_name: str = ""


@dataclass(slots=True)
class NormalizationOptions:
    """خيارات تطبيع صريحة؛ الخيارات الخطرة معطلة افتراضياً."""

    unicode_forms: bool = False
    arabic_digits_to_western: bool = False
    western_digits_to_arabic: bool = False
    remove_invisible: bool = False
    collapse_spaces: bool = False
    normalize_dashes: bool = False
    dash_underscore_equivalent: bool = False


@dataclass(slots=True)
class TransformationRule:
    """قاعدة تحويل مرتبة وقابلة للتسلسل إلى ملف تعريف."""

    kind: str
    value: str = ""
    replacement: str = ""
    enabled: bool = True
    target: str = "stem"


@dataclass(slots=True)
class PreflightCheck:
    """نتيجة عنصر واحد من قائمة الفحص القبلي."""

    code: str
    title: str
    level: PreflightLevel
    detail: str
    recommendation: str = ""


@dataclass(slots=True)
class ResultRecord:
    """نتيجة مطابقة ونسخ صورة واحدة أو معرّف واحد."""

    sequence: int
    excel_row: int
    original_value: str
    identifier: str
    match_status: MatchStatus
    source_path: Path | None = None
    destination_path: Path | None = None
    copy_status: CopyStatus = CopyStatus.NOT_REQUESTED
    notes: str = ""
    secondary_name: str = ""
    similarity_score: float | None = None
    match_explanation: str = ""
    candidate_paths: list[Path] = field(default_factory=list)
    selected_for_copy: bool = True
    manually_modified: bool = False
    reviewed: bool = False
    destination_filename_override: str = ""
    source_size: int = 0
    destination_size: int = 0
    destination_mtime_ns: int = 0
    destination_sha256: str = ""
    created_new_file: bool = False
    verified: bool = False

    @property
    def source_filename(self) -> str:
        return self.source_path.name if self.source_path else ""

    @property
    def destination_filename(self) -> str:
        return self.destination_path.name if self.destination_path else ""


@dataclass(slots=True)
class ProcessingSettings:
    """جميع مدخلات وخيارات مهمة المعالجة."""

    excel_path: Path
    worksheet: str
    column: ColumnInfo
    source_folder: Path
    destination_folder: Path
    recursive: bool = False
    case_insensitive: bool = True
    trim_identifiers: bool = True
    duplicate_policy: DuplicatePolicy = DuplicatePolicy.SKIP
    multiple_match_policy: MultipleMatchPolicy = MultipleMatchPolicy.FIRST
    generate_report: bool = True
    open_destination_after: bool = False
    ignore_duplicate_identifiers: bool = True
    matching_mode: MatchingMode = MatchingMode.EXACT
    normalization: NormalizationOptions = field(default_factory=NormalizationOptions)
    transformation_rules: list[TransformationRule] = field(default_factory=list)
    fuzzy_threshold: float = 0.82
    secondary_column: ColumnInfo | None = None
    start_row: int | None = None
    end_row: int | None = None
    dry_run: bool = False
    destination_folder_template: str = ""
    destination_filename_template: str = ""
    verify_hash: bool = False
    retry_count: int = 2
    retry_delay_seconds: float = 0.5
    copy_concurrency: int = 1
    profile_name: str = ""
    use_persistent_index: bool = True
    generate_manifest: bool = True
    batch_name: str = ""


@dataclass(slots=True)
class ProcessingStats:
    """إحصاءات المعالجة القابلة للعرض والتصدير."""

    total_excel_rows: int = 0
    empty_values: int = 0
    valid_identifiers: int = 0
    unique_identifiers: int = 0
    duplicate_identifiers: int = 0
    source_images_scanned: int = 0
    matched_identifiers: int = 0
    unmatched_identifiers: int = 0
    multiple_match_identifiers: int = 0
    copied_files: int = 0
    skipped_files: int = 0
    renamed_files: int = 0
    failed_copies: int = 0
    elapsed_seconds: float = 0.0
    estimated_copy_bytes: int = 0
    copied_bytes: int = 0

    def as_dict(self) -> dict[str, int | float]:
        """أعد نسخة قاموسية من الإحصاءات."""

        return asdict(self)


@dataclass(slots=True)
class JobResult:
    """ناتج مهمة معاينة أو نسخ كاملة."""

    settings: ProcessingSettings
    records: list[ResultRecord] = field(default_factory=list)
    stats: ProcessingStats = field(default_factory=ProcessingStats)
    report_path: Path | None = None
    log_path: Path | None = None
    cancelled: bool = False
    fatal_error: str = ""
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    finished_at: str = ""
    manifest_path: Path | None = None
    preflight_checks: list[PreflightCheck] = field(default_factory=list)
    profile_name: str = ""
    undone: bool = False

    @property
    def outcome(self) -> str:
        if self.fatal_error:
            return "failure"
        if self.cancelled:
            return "cancelled"
        if self.stats.unmatched_identifiers or self.stats.skipped_files or self.stats.failed_copies:
            return "partial"
        return "success"
