"""قوالب وجهة آمنة لنظام Windows تمنع اجتياز المسار."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from string import Formatter

_ILLEGAL_RE = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
ALLOWED_PLACEHOLDERS = {
    "identifier",
    "name",
    "excel_name",
    "worksheet",
    "date",
    "year",
    "month",
    "extension",
    "sequence",
}


def sanitize_component(value: object, fallback: str = "غير_معروف") -> str:
    """حوّل نصاً إلى مكوّن مسار Windows آمن."""

    cleaned = _ILLEGAL_RE.sub("_", str(value)).strip().rstrip(". ")
    if cleaned in {"", ".", ".."}:
        cleaned = fallback
    if cleaned.split(".", 1)[0].upper() in _RESERVED:
        cleaned = f"_{cleaned}"
    return cleaned[:180]


def validate_template(template: str) -> list[str]:
    """تحقق من القالب وأعد الأخطاء بدلاً من رفع استثناء غير مفهوم."""

    errors: list[str] = []
    if Path(template).is_absolute() or ".." in Path(template).parts:
        errors.append("لا يسمح القالب بمسار مطلق أو بالانتقال إلى المجلد الأب.")
    try:
        fields = {field for _, field, _, _ in Formatter().parse(template) if field}
    except ValueError as exc:
        return [f"تركيب القالب غير صالح: {exc}"]
    unknown = fields - ALLOWED_PLACEHOLDERS
    if unknown:
        errors.append(f"حقول غير معروفة: {', '.join(sorted(unknown))}")
    return errors


def render_template(template: str, values: dict[str, object], extension: str = "") -> str:
    """اعرض قالباً بعد تقييد الحقول وتعقيم كل مكوّن."""

    errors = validate_template(template)
    if errors:
        raise ValueError(" ".join(errors))
    today = date.today()
    context = {
        "identifier": values.get("identifier", ""),
        "name": values.get("name", ""),
        "excel_name": values.get("excel_name", ""),
        "worksheet": values.get("worksheet", ""),
        "date": today.isoformat(),
        "year": str(today.year),
        "month": f"{today.month:02d}",
        "extension": extension.lstrip("."),
        "sequence": values.get("sequence", ""),
    }
    safe = {key: sanitize_component(value) for key, value in context.items()}
    rendered = template.format_map(safe)
    parts = [sanitize_component(part) for part in re.split(r"[/\\]", rendered) if part not in {"", "."}]
    if not parts:
        raise ValueError("ينتج القالب مساراً فارغاً.")
    return str(Path(*parts))
