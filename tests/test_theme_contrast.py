"""Regression coverage for semantic colors and popup/table readability."""

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QComboBox, QPushButton, QTableWidget

from ui.dialogs import AppDialog
from ui.theme import PALETTES, apply_application_theme, stylesheet
from utils.contrast import audit_theme


def test_important_theme_pairs_meet_normal_text_contrast() -> None:
    for colors in PALETTES.values():
        ratios = audit_theme(colors)
        assert all(ratio >= 4.5 for ratio in ratios.values()), ratios


def test_qss_explicitly_styles_popups_tables_disabled_menus_and_tooltips() -> None:
    rules = stylesheet("dark")
    for selector in (
        "QComboBox QAbstractItemView",
        "QTableView::item:selected",
        "QPushButton:disabled",
        "QMenu",
        "QToolTip",
        "QDialog",
    ):
        assert selector in rules
    assert 'font-family: "Tajawal"' in rules


def test_palette_dialog_popup_table_and_disabled_controls_follow_both_themes(qtbot, qapp) -> None:
    app = qapp
    dialog = AppDialog("اختبار", "نص عربي واضح", details="تفاصيل")
    combo = QComboBox(dialog)
    combo.addItems(["الأول", "الثاني"])
    table = QTableWidget(1, 1, dialog)
    button = QPushButton("معطّل", dialog)
    button.setDisabled(True)
    qtbot.addWidget(dialog)
    for theme in ("light", "dark"):
        apply_application_theme(app, theme)
        palette = app.palette()
        assert palette.color(QPalette.ColorRole.WindowText) != palette.color(QPalette.ColorRole.Window)
        assert palette.color(QPalette.ColorRole.HighlightedText) != palette.color(QPalette.ColorRole.Highlight)
        assert combo.view().palette().color(QPalette.ColorRole.Text) != combo.view().palette().color(
            QPalette.ColorRole.Base
        )
        assert table.font().family() == "Tajawal"
        disabled = button.palette().color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText)
        background = button.palette().color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button)
        assert disabled != background


def test_open_dialog_updates_when_theme_changes(qtbot, qapp) -> None:
    dialog = AppDialog("العنوان", "رسالة قابلة للقراءة")
    qtbot.addWidget(dialog)
    dialog.open()
    apply_application_theme(qapp, "light")
    light = dialog.palette().color(QPalette.ColorRole.Window)
    apply_application_theme(qapp, "dark")
    dark = dialog.palette().color(QPalette.ColorRole.Window)
    assert light != dark
    assert dialog.isVisible()
    dialog.reject()
