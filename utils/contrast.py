"""Small WCAG-style contrast helpers used by the theme regression tests."""

from __future__ import annotations


def _luminance(color: str) -> float:
    value = color.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected #RRGGBB, received {color!r}")
    channels = [int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    """Return the WCAG contrast ratio between two opaque RGB colors."""

    lighter, darker = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def audit_theme(colors: dict[str, str]) -> dict[str, float]:
    """Audit the important semantic foreground/background pairs."""

    pairs = {
        "primary_text": ("text_primary", "background_primary"),
        "secondary_text": ("text_secondary", "surface_primary"),
        "dialog_text": ("dialog_text", "dialog_background"),
        "input_text": ("input_text", "input_background"),
        "input_placeholder": ("input_placeholder", "input_background"),
        "selection_text": ("selection_text", "selection_background"),
        "tooltip_text": ("tooltip_text", "tooltip_background"),
        "menu_text": ("menu_text", "menu_background"),
        "primary_button": ("text_on_primary", "primary"),
        "success_banner": ("text_on_success", "success"),
        "warning_banner": ("text_on_warning", "warning"),
        "error_banner": ("text_on_error", "error"),
    }
    return {name: contrast_ratio(colors[fg], colors[bg]) for name, (fg, bg) in pairs.items()}
