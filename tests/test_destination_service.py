"""اختبارات تعقيم وقوالب مسارات Windows."""

import pytest

from services.destination_service import render_template, sanitize_component, validate_template


def test_sanitizes_illegal_and_reserved_names() -> None:
    assert sanitize_component("AUX") == "_AUX"
    assert sanitize_component('name<>:"/\\|?*') == "name_________"


def test_safe_template_rendering() -> None:
    rendered = render_template("{excel_name}/{identifier}", {"excel_name": "دفعة:1", "identifier": "A/2"})
    assert rendered.endswith("دفعة_1\\A_2") or rendered.endswith("دفعة_1/A_2")


def test_path_traversal_and_unknown_fields_rejected() -> None:
    assert validate_template("../{identifier}")
    assert validate_template("{secret}")
    with pytest.raises(ValueError):
        render_template("../{identifier}", {"identifier": "1"})
