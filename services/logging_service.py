"""تهيئة سجل مستقل لكل عملية."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


def create_job_logger(log_directory: Path) -> tuple[logging.Logger, Path]:
    """أنشئ مسجلاً وملف سجل مؤرخاً داخل المجلد المحدد."""

    log_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    log_path = log_directory / f"image_copy_{timestamp}.log"
    logger = logging.getLogger(f"image_copy.{timestamp}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    return logger, log_path


def close_job_logger(logger: logging.Logger) -> None:
    """أغلق مقابض ملف السجل فور انتهاء المهمة."""

    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
