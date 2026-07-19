"""ثوابت التطبيق والنصوص المشتركة."""

from __future__ import annotations

APP_NAME = "مُطابق الصور"
APP_SECONDARY_NAME = "نظام مطابقة ونسخ الصور الذكي"
APP_TAGLINE = "طابق آلاف الصور مع بيانات Excel بدقة وسرعة."
APP_ORGANIZATION = "ImageCopyTool"
SETTINGS_APP_NAME = "نسخ الصور حسب الرقم الذاتي"
PRIVACY_STATEMENT = "تتم معالجة الملفات محلياً على جهازك ولا يتم رفعها إلى الإنترنت."
REQUIRED_HEADER = "الرقم الذاتي"
SUPPORTED_EXCEL_EXTENSIONS = {".xlsx", ".xlsm", ".csv", ".tsv"}
IDENTIFIER_HEADER_ALIASES = {
    "الرقم الذاتي",
    "الرقم",
    "رقم ذاتي",
    "الرقم الوظيفي",
    "المعرف",
    "الكود",
    "رقم الموظف",
    "رقم الطالب",
    "id",
    "identifier",
    "code",
}
SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
    ".heic",
    ".jfif",
}

MATCH_STATUS_AR = {
    "matched": "مطابق",
    "not_found": "غير موجود",
    "multiple": "أكثر من تطابق",
    "duplicate": "قيمة مكررة",
    "empty": "قيمة فارغة",
    "error": "خطأ",
    "fuzzy": "اقتراح تقريبي",
    "manual": "اختيار يدوي",
}

COPY_STATUS_AR = {
    "not_requested": "لم يبدأ النسخ",
    "copied": "تم النسخ",
    "skipped": "تم التخطي",
    "renamed": "تم النسخ باسم جديد",
    "failed": "فشل النسخ",
    "cancelled": "ملغى",
}

DUPLICATE_POLICY_AR = {
    "skip": "تخطي الملف الموجود",
    "overwrite": "استبدال الملف الموجود",
    "rename": "إنشاء اسم جديد تلقائياً",
}

MULTIPLE_POLICY_AR = {
    "first": "نسخ أول تطابق محدد",
    "all": "نسخ جميع الملفات المطابقة",
}
