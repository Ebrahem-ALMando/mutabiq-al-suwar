"""محرك المطابقة الذكي: دقيقة، مطبّعة، قواعد مرئية، واقتراحات فقط."""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from models.result_models import MatchingMode, ProcessingSettings, TransformationRule

_INVISIBLE_RE = re.compile(r"[\u200B-\u200F\u202A-\u202E\u2060\uFEFF]")
_SPACES_RE = re.compile(r"\s+")
_DASHES_RE = re.compile(r"[‐‑‒–—―−]")
_ARABIC_TO_WESTERN = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_WESTERN_TO_ARABIC = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


@dataclass(frozen=True, slots=True)
class FuzzySuggestion:
    """اقتراح غير معتمد مع درجة وسبب مفهوم."""

    key: str
    paths: tuple[Path, ...]
    score: float
    explanation: str


def apply_transformation_rules(value: str, rules: list[TransformationRule], target: str) -> str:
    """طبّق القواعد المرئية المرتبة على المعرّف أو ساق الصورة."""

    transformed = value
    for rule in rules:
        if not rule.enabled or rule.target not in {target, "both"}:
            continue
        if rule.kind == "trim":
            transformed = transformed.strip()
        elif rule.kind == "remove_prefix" and rule.value and transformed.startswith(rule.value):
            transformed = transformed[len(rule.value) :]
        elif rule.kind == "remove_suffix" and rule.value and transformed.endswith(rule.value):
            transformed = transformed[: -len(rule.value)]
        elif rule.kind == "remove_text":
            transformed = transformed.replace(rule.value, "")
        elif rule.kind == "replace":
            transformed = transformed.replace(rule.value, rule.replacement)
        elif rule.kind == "lower":
            transformed = transformed.lower()
        elif rule.kind == "upper":
            transformed = transformed.upper()
        elif rule.kind == "between":
            start, separator, end = rule.value.partition("|")
            if separator and start in transformed:
                remainder = transformed.split(start, 1)[1]
                if end in remainder:
                    transformed = remainder.split(end, 1)[0]
        elif rule.kind == "regex_capture":
            match = re.search(rule.value, transformed)
            if match:
                group = int(rule.replacement or "1")
                transformed = match.group(group)
    return transformed


def validate_transformation_rule(rule: TransformationRule) -> str | None:
    """أعد رسالة خطأ عند عدم صلاحية قاعدة من دون تنفيذ أي شيفرة."""

    allowed = {
        "trim",
        "remove_prefix",
        "remove_suffix",
        "remove_text",
        "replace",
        "lower",
        "upper",
        "between",
        "regex_capture",
    }
    if rule.kind not in allowed:
        return "نوع قاعدة غير مدعوم."
    if rule.kind == "regex_capture":
        try:
            compiled = re.compile(rule.value)
            group = int(rule.replacement or "1")
            if group < 0 or group > compiled.groups:
                return "مجموعة الالتقاط المطلوبة غير موجودة."
        except (re.error, ValueError) as exc:
            return f"تعبير نمطي غير صالح: {exc}"
    if rule.kind == "between" and "|" not in rule.value:
        return "قاعدة ما بين المحددين تحتاج الصيغة: بداية|نهاية."
    return None


class SmartMatchingEngine:
    """ينشئ مفاتيح آمنة ويولّد اقتراحات لا تُنسخ تلقائياً."""

    def normalize(self, value: str, settings: ProcessingSettings, target: str) -> str:
        """طبّع قيمة وفق الخيارات التي وافق عليها المستخدم فقط."""

        result = value.strip() if settings.trim_identifiers and target == "identifier" else value
        options = settings.normalization
        if settings.matching_mode in {MatchingMode.NORMALIZED, MatchingMode.PATTERN, MatchingMode.FUZZY}:
            if options.unicode_forms:
                result = unicodedata.normalize("NFKC", result)
            if options.arabic_digits_to_western:
                result = result.translate(_ARABIC_TO_WESTERN)
            if options.western_digits_to_arabic:
                result = result.translate(_WESTERN_TO_ARABIC)
            if options.remove_invisible:
                result = _INVISIBLE_RE.sub("", result)
            if options.collapse_spaces:
                result = _SPACES_RE.sub(" ", result)
            if options.normalize_dashes:
                result = _DASHES_RE.sub("-", result)
            if options.dash_underscore_equivalent:
                result = result.replace("_", "-")
        if settings.matching_mode in {MatchingMode.PATTERN, MatchingMode.FUZZY}:
            result = apply_transformation_rules(result, settings.transformation_rules, target)
        if settings.case_insensitive:
            result = result.casefold()
        return result

    def identifier_key(self, value: str, settings: ProcessingSettings) -> str:
        return self.normalize(value, settings, "identifier")

    def stem_key(self, value: str, settings: ProcessingSettings) -> str:
        return self.normalize(value, settings, "stem")

    def suggestions(
        self,
        index: dict[str, list[Path]],
        identifier: str,
        settings: ProcessingSettings,
        maximum: int = 5,
    ) -> list[FuzzySuggestion]:
        """ولّد أفضل اقتراحات؛ لا تغيّر قرار النسخ ولا تختار ملفاً."""

        wanted = self.identifier_key(identifier, settings)
        if not wanted:
            return []
        candidates: list[tuple[float, str]] = []
        for key in index:
            if abs(len(key) - len(wanted)) > max(3, len(wanted) // 3):
                continue
            score = difflib.SequenceMatcher(None, wanted, key, autojunk=False).ratio()
            if score >= settings.fuzzy_threshold:
                candidates.append((score, key))
        candidates.sort(key=lambda item: (-item[0], item[1]))
        suggestions: list[FuzzySuggestion] = []
        for score, key in candidates[:maximum]:
            if score >= 0.95:
                label = "مرجح جداً؛ اختلاف بسيط في حرف أو فاصل."
            elif score >= 0.85:
                label = "اقتراح محتمل يحتاج مراجعة."
            else:
                label = "اقتراح ضعيف يحتاج تدقيقاً يدوياً."
            suggestions.append(FuzzySuggestion(key, tuple(index[key]), score, label))
        return suggestions
