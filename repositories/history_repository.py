"""قاعدة SQLite ذات ترحيلات لسجل العمليات والفهرس والإشعارات."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from models.result_models import JobResult
from utils.constants import SUPPORTED_IMAGE_EXTENSIONS
from utils.path_helpers import is_path_within
from utils.version import DATABASE_SCHEMA_VERSION


class ClosingConnection(sqlite3.Connection):
    """اتصال يغلق المقبض فعلياً عند مغادرة سياق with على Windows."""

    def __exit__(self, exc_type, exc_value, traceback) -> Literal[False]:
        try:
            super().__exit__(exc_type, exc_value, traceback)
            return False
        finally:
            self.close()


def _json_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: _json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    return value


class HistoryRepository:
    """واجهة معاملات قصيرة وآمنة لسجل وبيانات الفهرسة المحلية."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.migrate()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30, factory=ClosingConnection)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def migrate(self) -> None:
        """طبّق الترحيلات التزايدية، مع نسخة قبل قاعدة قائمة قديمة."""

        existing = self.database_path.exists() and self.database_path.stat().st_size > 0
        with self.connect() as connection:
            current = connection.execute("PRAGMA user_version").fetchone()[0]
        if current > DATABASE_SCHEMA_VERSION:
            raise RuntimeError("قاعدة البيانات أنشئت بإصدار أحدث من التطبيق.")
        if existing and 0 < current < DATABASE_SCHEMA_VERSION:
            backup = self.database_path.with_name(
                f"{self.database_path.stem}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
            )
            shutil.copy2(self.database_path, backup)
        if current < 1:
            with self.connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS batches (
                        batch_id TEXT PRIMARY KEY,
                        parent_batch_id TEXT,
                        batch_name TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        finished_at TEXT,
                        excel_path TEXT NOT NULL,
                        excel_filename TEXT NOT NULL,
                        worksheet TEXT,
                        source_folder TEXT NOT NULL,
                        destination_folder TEXT NOT NULL,
                        profile_name TEXT,
                        settings_json TEXT NOT NULL,
                        total_identifiers INTEGER NOT NULL DEFAULT 0,
                        matched_count INTEGER NOT NULL DEFAULT 0,
                        copied_count INTEGER NOT NULL DEFAULT 0,
                        unmatched_count INTEGER NOT NULL DEFAULT 0,
                        multiple_count INTEGER NOT NULL DEFAULT 0,
                        failed_count INTEGER NOT NULL DEFAULT 0,
                        copied_bytes INTEGER NOT NULL DEFAULT 0,
                        duration_seconds REAL NOT NULL DEFAULT 0,
                        status TEXT NOT NULL,
                        dry_run INTEGER NOT NULL DEFAULT 0,
                        undone_status TEXT NOT NULL DEFAULT 'not_undone',
                        report_path TEXT,
                        manifest_path TEXT,
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_batches_started ON batches(started_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_batches_status ON batches(status);
                    CREATE INDEX IF NOT EXISTS idx_batches_excel ON batches(excel_filename);

                    CREATE TABLE IF NOT EXISTS batch_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        batch_id TEXT NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
                        sequence INTEGER NOT NULL,
                        excel_row INTEGER NOT NULL,
                        identifier TEXT,
                        secondary_name TEXT,
                        match_status TEXT NOT NULL,
                        source_path TEXT,
                        destination_path TEXT,
                        copy_status TEXT NOT NULL,
                        similarity_score REAL,
                        manually_modified INTEGER NOT NULL DEFAULT 0,
                        created_new_file INTEGER NOT NULL DEFAULT 0,
                        destination_size INTEGER NOT NULL DEFAULT 0,
                        destination_mtime_ns INTEGER NOT NULL DEFAULT 0,
                        destination_sha256 TEXT,
                        verified INTEGER NOT NULL DEFAULT 0,
                        notes TEXT
                    );
                    CREATE INDEX IF NOT EXISTS idx_items_batch ON batch_items(batch_id);
                    CREATE INDEX IF NOT EXISTS idx_items_identifier ON batch_items(identifier);
                    CREATE INDEX IF NOT EXISTS idx_items_status ON batch_items(match_status, copy_status);

                    CREATE TABLE IF NOT EXISTS indexed_folders (
                        folder_id TEXT PRIMARY KEY,
                        absolute_path TEXT NOT NULL,
                        recursive INTEGER NOT NULL,
                        image_count INTEGER NOT NULL DEFAULT 0,
                        total_bytes INTEGER NOT NULL DEFAULT 0,
                        last_scan TEXT,
                        UNIQUE(absolute_path, recursive)
                    );
                    CREATE TABLE IF NOT EXISTS image_index (
                        folder_id TEXT NOT NULL REFERENCES indexed_folders(folder_id) ON DELETE CASCADE,
                        absolute_path TEXT NOT NULL,
                        relative_path TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        stem TEXT NOT NULL,
                        extension TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        modified_ns INTEGER NOT NULL,
                        content_hash TEXT,
                        scan_date TEXT NOT NULL,
                        PRIMARY KEY(folder_id, absolute_path)
                    );
                    CREATE INDEX IF NOT EXISTS idx_images_stem ON image_index(folder_id, stem);
                    CREATE INDEX IF NOT EXISTS idx_images_extension ON image_index(extension);

                    CREATE TABLE IF NOT EXISTS notifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        severity TEXT NOT NULL,
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        batch_id TEXT,
                        created_at TEXT NOT NULL,
                        dismissed INTEGER NOT NULL DEFAULT 0
                    );
                    CREATE INDEX IF NOT EXISTS idx_notifications_active ON notifications(dismissed, created_at DESC);
                    PRAGMA user_version=1;
                    """
                )

    def record_result(self, result: JobResult, parent_batch_id: str | None = None) -> None:
        """سجّل دفعة وعناصرها في معاملة واحدة."""

        settings = result.settings
        with self.connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO batches (
                    batch_id,parent_batch_id,batch_name,started_at,finished_at,excel_path,excel_filename,
                    worksheet,source_folder,destination_folder,profile_name,settings_json,total_identifiers,
                    matched_count,copied_count,unmatched_count,multiple_count,failed_count,copied_bytes,
                    duration_seconds,status,dry_run,undone_status,report_path,manifest_path,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    result.batch_id,
                    parent_batch_id,
                    settings.batch_name or settings.excel_path.stem,
                    result.started_at,
                    result.finished_at,
                    str(settings.excel_path),
                    settings.excel_path.name,
                    settings.worksheet,
                    str(settings.source_folder),
                    str(settings.destination_folder),
                    settings.profile_name,
                    json.dumps(_json_value(settings), ensure_ascii=False),
                    result.stats.valid_identifiers,
                    result.stats.matched_identifiers,
                    result.stats.copied_files,
                    result.stats.unmatched_identifiers,
                    result.stats.multiple_match_identifiers,
                    result.stats.failed_copies,
                    result.stats.copied_bytes,
                    result.stats.elapsed_seconds,
                    result.outcome,
                    int(settings.dry_run),
                    "not_undone",
                    str(result.report_path or ""),
                    str(result.manifest_path or ""),
                    datetime.now(UTC).isoformat(),
                ),
            )
            connection.execute("DELETE FROM batch_items WHERE batch_id=?", (result.batch_id,))
            connection.executemany(
                """INSERT INTO batch_items (
                    batch_id,sequence,excel_row,identifier,secondary_name,match_status,source_path,
                    destination_path,copy_status,similarity_score,manually_modified,created_new_file,
                    destination_size,destination_mtime_ns,destination_sha256,verified,notes
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [
                    (
                        result.batch_id,
                        record.sequence,
                        record.excel_row,
                        record.identifier,
                        record.secondary_name,
                        record.match_status.value,
                        str(record.source_path or ""),
                        str(record.destination_path or ""),
                        record.copy_status.value,
                        record.similarity_score,
                        int(record.manually_modified),
                        int(record.created_new_file),
                        record.destination_size,
                        record.destination_mtime_ns,
                        record.destination_sha256,
                        int(record.verified),
                        record.notes,
                    )
                    for record in result.records
                ],
            )
            severity = (
                "success"
                if result.outcome == "success"
                else "warning" if result.outcome in {"partial", "cancelled"} else "error"
            )
            connection.execute(
                "INSERT INTO notifications(severity,title,message,batch_id,created_at) VALUES(?,?,?,?,?)",
                (
                    severity,
                    "اكتملت عملية مطابقة الصور",
                    f"الحالة: {result.outcome}",
                    result.batch_id,
                    datetime.now(UTC).isoformat(),
                ),
            )

    def recent_batches(self, limit: int = 50, search: str = "", status: str = "") -> list[dict[str, Any]]:
        query = "SELECT * FROM batches WHERE 1=1"
        parameters: list[Any] = []
        if search:
            query += (
                " AND (batch_id LIKE ? OR excel_filename LIKE ? OR source_folder LIKE ? OR destination_folder LIKE ?)"
            )
            term = f"%{search}%"
            parameters.extend([term] * 4)
        if status:
            query += " AND status=?"
            parameters.append(status)
        query += " ORDER BY started_at DESC LIMIT ?"
        parameters.append(limit)
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(query, parameters).fetchall()]

    def batch(self, batch_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM batches WHERE batch_id=?", (batch_id,)).fetchone()
            return dict(row) if row else None

    def batch_items(self, batch_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM batch_items WHERE batch_id=? ORDER BY sequence,id", (batch_id,)
                )
            ]

    def dashboard(self) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT COUNT(*) batches, COALESCE(SUM(total_identifiers),0) identifiers,
                COALESCE(SUM(matched_count),0) matched, COALESCE(SUM(unmatched_count),0) unmatched,
                COALESCE(SUM(copied_count),0) copied, COALESCE(SUM(copied_bytes),0) copied_bytes,
                COALESCE(AVG(duration_seconds),0) average_seconds, MAX(started_at) last_operation
                FROM batches"""
            ).fetchone()
            data = dict(row)
            latest = connection.execute("SELECT source_folder FROM batches ORDER BY started_at DESC LIMIT 1").fetchone()
            data["recent_source"] = latest[0] if latest else ""
            data["match_rate"] = (data["matched"] / data["identifiers"] * 100) if data["identifiers"] else 0.0
            return data

    def history_series(self, limit: int = 12) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT started_at,total_identifiers,matched_count,unmatched_count,multiple_count,failed_count FROM batches ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in reversed(rows)]

    def extension_distribution(self) -> dict[str, int]:
        with self.connect() as connection:
            rows = connection.execute("SELECT extension,COUNT(*) count FROM image_index GROUP BY extension").fetchall()
        result = {"JPG": 0, "PNG": 0, "WEBP": 0, "أخرى": 0}
        for row in rows:
            extension = str(row["extension"]).lower()
            key = (
                "JPG"
                if extension in {".jpg", ".jpeg", ".jfif"}
                else "PNG" if extension == ".png" else "WEBP" if extension == ".webp" else "أخرى"
            )
            result[key] += int(row["count"])
        return result

    def mark_undo(self, batch_id: str, status: str) -> None:
        with self.connect() as connection:
            connection.execute("UPDATE batches SET undone_status=? WHERE batch_id=?", (status, batch_id))

    def clear_history(self) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM batches")
            connection.execute("DELETE FROM notifications")

    def active_notifications(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM notifications WHERE dismissed=0 ORDER BY created_at DESC LIMIT ?", (limit,)
                )
            ]

    def dismiss_notification(self, notification_id: int) -> None:
        with self.connect() as connection:
            connection.execute("UPDATE notifications SET dismissed=1 WHERE id=?", (notification_id,))

    def refresh_image_index(
        self,
        source: Path,
        recursive: bool,
        key_transform: Callable[[str], str],
        excluded: Path | None = None,
        cancelled: Callable[[], bool] | None = None,
        progress: Callable[[int, int, str], None] | None = None,
    ) -> tuple[dict[str, list[Path]], int]:
        """حدّث فهرس مجلد بكتابات مجمعة وأعد مفاتيح المطابقة."""

        resolved_source = source.resolve()
        folder_id = hashlib.sha256(f"{resolved_source}|{recursive}".encode()).hexdigest()
        iterator = source.rglob("*") if recursive else source.glob("*")
        rows: list[tuple] = []
        index: dict[str, list[Path]] = {}
        seen_paths: set[str] = set()
        total_bytes = 0
        scanned_at = datetime.now(UTC).isoformat()
        for path in iterator:
            if cancelled and cancelled():
                break
            try:
                if not path.is_file() or path.suffix.casefold() not in SUPPORTED_IMAGE_EXTENSIONS:
                    continue
                if excluded and is_path_within(path, excluded):
                    continue
                stat = path.stat()
                absolute = str(path.resolve())
                seen_paths.add(absolute)
                total_bytes += stat.st_size
                key = key_transform(path.stem)
                index.setdefault(key, []).append(path)
                rows.append(
                    (
                        folder_id,
                        absolute,
                        str(path.relative_to(source)),
                        path.name,
                        key,
                        path.suffix.casefold(),
                        stat.st_size,
                        stat.st_mtime_ns,
                        None,
                        scanned_at,
                    )
                )
                if progress and len(rows) % 100 == 0:
                    progress(len(rows), 0, path.name)
            except OSError:
                continue
        with self.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO indexed_folders(folder_id,absolute_path,recursive,image_count,total_bytes,last_scan) VALUES(?,?,?,?,?,?)",
                (folder_id, str(resolved_source), int(recursive), len(rows), total_bytes, scanned_at),
            )
            connection.executemany(
                """INSERT OR REPLACE INTO image_index(folder_id,absolute_path,relative_path,filename,stem,extension,file_size,modified_ns,content_hash,scan_date)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                rows,
            )
            existing = {
                row[0]
                for row in connection.execute("SELECT absolute_path FROM image_index WHERE folder_id=?", (folder_id,))
            }
            removed = existing - seen_paths
            connection.executemany(
                "DELETE FROM image_index WHERE folder_id=? AND absolute_path=?", [(folder_id, path) for path in removed]
            )
        deterministic = {
            key: sorted(paths, key=lambda item: (str(item).casefold(), str(item))) for key, paths in index.items()
        }
        if progress:
            progress(len(rows), len(rows), "")
        return deterministic, len(rows)

    def indexed_folders(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM indexed_folders ORDER BY last_scan DESC")]

    def remove_index(self, folder_id: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM indexed_folders WHERE folder_id=?", (folder_id,))
