"""اختبارات التطبيع والقواعد والاقتراحات غير التلقائية."""

from pathlib import Path

from models.result_models import ColumnInfo, MatchingMode, NormalizationOptions, ProcessingSettings, TransformationRule
from services.matching_service import SmartMatchingEngine, apply_transformation_rules, validate_transformation_rule


def settings(tmp_path, mode=MatchingMode.EXACT, **kwargs):
    return ProcessingSettings(
        tmp_path / "x.xlsx",
        "Sheet",
        ColumnInfo(1, "ID", "A"),
        tmp_path,
        tmp_path / "out",
        matching_mode=mode,
        **kwargs,
    )


def test_normalization_is_explicit(tmp_path) -> None:
    engine = SmartMatchingEngine()
    exact = settings(tmp_path)
    normalized = settings(
        tmp_path,
        MatchingMode.NORMALIZED,
        normalization=NormalizationOptions(arabic_digits_to_western=True, normalize_dashes=True),
    )
    assert engine.identifier_key("١٢٣–٤", exact) != "123-4"
    assert engine.identifier_key("١٢٣–٤", normalized) == "123-4"


def test_ordered_pattern_rules() -> None:
    rules = [TransformationRule("remove_prefix", "IMG_"), TransformationRule("remove_suffix", "_front")]
    assert apply_transformation_rules("IMG_A123_front", rules, "stem") == "A123"


def test_regex_rule_validation_and_capture() -> None:
    valid = TransformationRule("regex_capture", r"employee_(.+)_photo", "1")
    invalid = TransformationRule("regex_capture", "(", "1")
    assert validate_transformation_rule(valid) is None
    assert validate_transformation_rule(invalid)
    assert apply_transformation_rules("employee_A77_photo", [valid], "stem") == "A77"


def test_fuzzy_suggestion_has_score_but_does_not_select(tmp_path) -> None:
    config = settings(tmp_path, MatchingMode.FUZZY, fuzzy_threshold=0.7)
    suggestions = SmartMatchingEngine().suggestions({"a3222263": [Path("a3222263.jpg")]}, "a322263", config)
    assert suggestions
    assert suggestions[0].score >= 0.7
    assert "مراجعة" in suggestions[0].explanation or "مرجح" in suggestions[0].explanation
