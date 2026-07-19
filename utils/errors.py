"""أخطاء نطاقية ذات رموز ثابتة ورسائل آمنة للمستخدم."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class UserError(Exception):
    """خطأ قابل للعرض من دون كشف traceback."""

    code: str
    title: str
    message: str
    recommendation: str = "راجع المدخلات ثم أعد المحاولة."
    technical_details: str = ""

    def __str__(self) -> str:
        return self.message


class ValidationError(UserError):
    """خطأ تحقق يمنع بدء العملية."""


class ManifestError(UserError):
    """خطأ إنشاء أو قراءة منشور العملية."""


class UnsafeUndoError(UserError):
    """محاولة تراجع لا تحقق شروط السلامة."""
