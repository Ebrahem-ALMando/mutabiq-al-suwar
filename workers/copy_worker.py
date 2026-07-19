"""عامل Qt ينفّذ خط المعالجة خارج خيط الواجهة."""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from models.result_models import ProcessingSettings
from repositories.history_repository import HistoryRepository
from services.logging_service import close_job_logger, create_job_logger
from services.manifest_service import ManifestService
from services.processing_service import ProcessingService
from utils.app_paths import AppPaths


class CopyWorker(QObject):
    """غلاف إشارات Qt لخدمة المعالجة القابلة للإلغاء."""

    progress = Signal(str, str, int, int, str, object)
    processing_completed = Signal(str, object)
    processing_failed = Signal(str, str, str)
    processing_cancelled = Signal(str, object)
    worker_finished = Signal()

    def __init__(
        self,
        settings: ProcessingSettings,
        preview_only: bool,
        log_directory: Path,
        app_paths: AppPaths | None = None,
        prepared_result=None,
        operation_id: str = "",
    ) -> None:
        super().__init__()
        self.settings = settings
        self.preview_only = preview_only
        self.log_directory = log_directory
        self.app_paths = app_paths
        self.prepared_result = prepared_result
        self.operation_id = operation_id
        self._cancel_event = threading.Event()
        self._pause_condition = threading.Condition()
        self._paused = False
        self._terminal_emitted = False

    def _emit_terminal(self, kind: str, *args) -> None:
        if self._terminal_emitted:
            return
        self._terminal_emitted = True
        if kind == "completed":
            self.processing_completed.emit(self.operation_id, *args)
        elif kind == "cancelled":
            self.processing_cancelled.emit(self.operation_id, *args)
        else:
            self.processing_failed.emit(self.operation_id, *args)

    @Slot()
    def run(self) -> None:
        """ابدأ المهمة وأرسل النتيجة أو رسالة خطأ عربية موجزة."""

        logger = None
        log_path = self.log_directory
        try:
            logger, log_path = create_job_logger(self.log_directory)
            history = HistoryRepository(self.app_paths.database) if self.app_paths else None
            manifests = ManifestService(self.app_paths.manifests) if self.app_paths else None
            service = ProcessingService(history, manifests)
            result = service.run(
                self.settings,
                self.preview_only,
                logger,
                event=lambda stage, current, total, item, stats: self.progress.emit(
                    self.operation_id, stage, current, total, item, stats
                ),
                cancelled=self._cancel_event.is_set,
                wait_if_paused=self._wait_if_paused,
                overrides=self.prepared_result,
            )
            result.log_path = log_path
            if result.cancelled:
                logger.warning("ألغى المستخدم العملية")
                self._emit_terminal("cancelled", result)
            else:
                self._emit_terminal("completed", result)
        except (FileNotFoundError, PermissionError, ValueError, RuntimeError) as exc:
            if logger:
                logger.exception("تعذر إكمال العملية")
            self._emit_terminal("failed", str(exc), str(log_path))
        except Exception:
            if logger:
                logger.exception("خطأ غير متوقع")
            self._emit_terminal("failed", "حدث خطأ غير متوقع. راجع ملف السجل للتفاصيل.", str(log_path))
        finally:
            if logger:
                close_job_logger(logger)
            if not self._terminal_emitted:
                self._emit_terminal("failed", "انتهى العامل دون نتيجة نهائية.", str(log_path))
            self.worker_finished.emit()

    @Slot()
    def cancel(self) -> None:
        """اطلب الإلغاء الآمن بين الملفات."""

        self._cancel_event.set()
        self.resume()

    @Slot()
    def pause(self) -> None:
        """أوقف بدء العمليات التالية بعد انتهاء العملية الذرية الحالية."""

        with self._pause_condition:
            self._paused = True

    @Slot()
    def resume(self) -> None:
        """تابع العامل المتوقف مؤقتاً."""

        with self._pause_condition:
            self._paused = False
            self._pause_condition.notify_all()

    def _wait_if_paused(self) -> None:
        with self._pause_condition:
            while self._paused and not self._cancel_event.is_set():
                self._pause_condition.wait(timeout=0.25)
