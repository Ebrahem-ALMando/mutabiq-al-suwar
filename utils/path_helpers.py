"""وظائف آمنة للتعامل مع المسارات وفتحها."""

from __future__ import annotations

from pathlib import Path


def is_path_within(path: Path, parent: Path) -> bool:
    """تحقق مما إذا كان المسار داخل مجلد محدد بعد حل المسارين."""

    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (OSError, ValueError):
        return False


def unique_destination(path: Path) -> Path:
    """ولّد اسماً غير مستخدم بإضافة رقم متسلسل قبل الامتداد."""

    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1
