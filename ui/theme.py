"""Central semantic Qt palette and QSS generation for light and dark modes."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True, slots=True)
class DesignTokens:
    spacing: tuple[int, ...] = (0, 4, 8, 12, 16, 20, 24, 32, 40)
    radii: tuple[int, ...] = (4, 8, 12, 16, 22)
    animation_fast: int = 120
    animation_normal: int = 180
    input_height: int = 40
    button_height: int = 40


TOKENS = DesignTokens()

PALETTES: dict[str, dict[str, str]] = {
    "light": {
        "background_primary": "#F3F6F8", "background_secondary": "#E9EFF3",
        "surface_primary": "#FFFFFF", "surface_secondary": "#EAF0F3", "surface_elevated": "#FFFFFF",
        "surface_hover": "#E1F1F2", "surface_pressed": "#CDE7E9", "surface_selected": "#D4ECEE",
        "surface_disabled": "#E3E8EB", "text_primary": "#142A3A", "text_secondary": "#415866",
        "text_muted": "#5D707B", "text_disabled": "#687982", "text_on_primary": "#FFFFFF",
        "text_on_success": "#FFFFFF", "text_on_warning": "#1C1608", "text_on_error": "#FFFFFF",
        "border_default": "#B8C7CF", "border_subtle": "#D7E1E6", "border_focus": "#087B83",
        "primary": "#087B83", "primary_hover": "#066970", "primary_pressed": "#05575D",
        "success": "#13734E", "success_background": "#DDF4E9", "warning": "#D99A19",
        "warning_background": "#FFF1CE", "error": "#B93640", "error_background": "#FBE3E5",
        "info": "#1769A6", "info_background": "#DDEDFC", "selection_background": "#087B83",
        "selection_text": "#FFFFFF", "input_background": "#FFFFFF", "input_text": "#142A3A",
        "input_placeholder": "#667985", "tooltip_background": "#102E42", "tooltip_text": "#FFFFFF",
        "menu_background": "#FFFFFF", "menu_text": "#142A3A", "dialog_background": "#FFFFFF",
        "dialog_text": "#142A3A", "overlay_background": "#52606B", "scrollbar_track": "#E5EBEF",
        "scrollbar_handle": "#8799A4", "nav_background": "#102E42", "nav_text": "#E5F0F4",
    },
    "dark": {
        "background_primary": "#0D1821", "background_secondary": "#101F29",
        "surface_primary": "#14232E", "surface_secondary": "#1A2D39", "surface_elevated": "#203542",
        "surface_hover": "#23424C", "surface_pressed": "#294D57", "surface_selected": "#174C51",
        "surface_disabled": "#22323C", "text_primary": "#EDF5F7", "text_secondary": "#C4D1D7",
        "text_muted": "#A8B7BF", "text_disabled": "#8B9AA2", "text_on_primary": "#071719",
        "text_on_success": "#071A11", "text_on_warning": "#1A1406", "text_on_error": "#21090B",
        "border_default": "#4C6471", "border_subtle": "#304854", "border_focus": "#64D4D5",
        "primary": "#65D4D5", "primary_hover": "#82E0E1", "primary_pressed": "#46BABB",
        "success": "#68D8A4", "success_background": "#15392C", "warning": "#F2C45C",
        "warning_background": "#453616", "error": "#FA8C92", "error_background": "#472126",
        "info": "#83C7F4", "info_background": "#19394E", "selection_background": "#65D4D5",
        "selection_text": "#071719", "input_background": "#182A35", "input_text": "#EDF5F7",
        "input_placeholder": "#A5B4BC", "tooltip_background": "#EDF5F7", "tooltip_text": "#0D1821",
        "menu_background": "#203542", "menu_text": "#EDF5F7", "dialog_background": "#14232E",
        "dialog_text": "#EDF5F7", "overlay_background": "#05090D", "scrollbar_track": "#162630",
        "scrollbar_handle": "#647C89", "nav_background": "#09141C", "nav_text": "#E2EEF2",
    },
}


def colors_for(theme: str, high_contrast: bool = False) -> dict[str, str]:
    colors = dict(PALETTES.get(theme, PALETTES["light"]))
    if high_contrast:
        colors["border_default"] = colors["text_primary"]
        colors["border_focus"] = "#FFD54A"
    return colors


def qt_palette(theme: str = "light", high_contrast: bool = False) -> QPalette:
    c = colors_for(theme, high_contrast)
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: "background_primary", QPalette.ColorRole.WindowText: "text_primary",
        QPalette.ColorRole.Base: "input_background", QPalette.ColorRole.AlternateBase: "surface_secondary",
        QPalette.ColorRole.ToolTipBase: "tooltip_background", QPalette.ColorRole.ToolTipText: "tooltip_text",
        QPalette.ColorRole.Text: "input_text", QPalette.ColorRole.Button: "surface_primary",
        QPalette.ColorRole.ButtonText: "text_primary", QPalette.ColorRole.Highlight: "selection_background",
        QPalette.ColorRole.HighlightedText: "selection_text", QPalette.ColorRole.PlaceholderText: "input_placeholder",
        QPalette.ColorRole.Link: "info",
    }
    for role, token in roles.items():
        palette.setColor(QPalette.ColorGroup.All, role, QColor(c[token]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(c["text_disabled"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(c["text_disabled"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(c["text_disabled"]))
    return palette


def apply_application_theme(app: QApplication, theme: str, large_text: bool = False, high_contrast: bool = False) -> None:
    app.setPalette(qt_palette(theme, high_contrast))
    app.setStyleSheet(stylesheet(theme, large_text, high_contrast))
    for widget in app.topLevelWidgets():
        widget.setPalette(app.palette())
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()


def stylesheet(theme: str = "light", large_text: bool = False, high_contrast: bool = False) -> str:
    c = colors_for(theme, high_contrast)
    size = 14 if large_text else 13
    return f"""
    * {{ font-family: "Tajawal", "Segoe UI", Arial; font-size: {size}px; }}
    QMainWindow, QWidget#appRoot {{ background: {c['background_primary']}; color: {c['text_primary']}; }}
    QWidget {{ color: {c['text_primary']}; }}
    QDialog, QMessageBox {{ background: {c['dialog_background']}; color: {c['dialog_text']}; }}
    QDialog QLabel, QMessageBox QLabel {{ background: transparent; color: {c['dialog_text']}; }}
    QFrame#sidebar {{ background: {c['nav_background']}; border: none; }}
    QFrame#topbar, QFrame#card {{ background: {c['surface_primary']}; border: 1px solid {c['border_subtle']}; border-radius: 12px; }}
    QLabel {{ color: {c['text_primary']}; background: transparent; }}
    QLabel#productName {{ color: {c['nav_text']}; font-size: 18px; font-weight: 700; }}
    QLabel#pageTitle {{ color: {c['text_primary']}; font-size: 23px; font-weight: 700; }}
    QLabel#pageDescription, QLabel#muted {{ color: {c['text_muted']}; }}
    QLabel#sectionTitle {{ color: {c['text_primary']}; font-size: 16px; font-weight: 600; }}
    QLabel#statValue {{ color: {c['primary']}; font-size: 24px; font-weight: 700; }}
    QLabel[severity="success"] {{ color: {c['success']}; }}
    QLabel[severity="warning"] {{ color: {c['warning']}; }}
    QLabel[severity="error"] {{ color: {c['error']}; }}
    QPushButton, QToolButton {{ color: {c['text_primary']}; min-height: {TOKENS.button_height}px; padding: 0 14px; border-radius: 8px; border: 1px solid {c['border_default']}; background: {c['surface_primary']}; }}
    QPushButton:hover, QToolButton:hover {{ background: {c['surface_hover']}; border-color: {c['primary']}; }}
    QPushButton:pressed, QToolButton:pressed {{ background: {c['surface_pressed']}; }}
    QPushButton:focus, QToolButton:focus {{ border: 2px solid {c['border_focus']}; }}
    QPushButton:disabled, QToolButton:disabled {{ color: {c['text_disabled']}; background: {c['surface_disabled']}; border-color: {c['border_subtle']}; }}
    QPushButton#primary {{ color: {c['text_on_primary']}; border-color: {c['primary']}; background: {c['primary']}; font-weight: 700; }}
    QPushButton#primary:hover {{ background: {c['primary_hover']}; }} QPushButton#primary:pressed {{ background: {c['primary_pressed']}; }}
    QPushButton#navButton {{ color: {c['nav_text']}; text-align: right; border: none; background: transparent; padding: 0 14px; }}
    QPushButton#navButton:hover {{ background: {c['surface_hover']}; color: {c['text_primary']}; }}
    QPushButton#navButton:checked {{ background: {c['primary']}; color: {c['text_on_primary']}; font-weight: 700; }}
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{ color: {c['input_text']}; background: {c['input_background']}; selection-color: {c['selection_text']}; selection-background-color: {c['selection_background']}; min-height: {TOKENS.input_height}px; border: 1px solid {c['border_default']}; border-radius: 8px; padding: 0 10px; }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{ border: 2px solid {c['border_focus']}; }}
    QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled {{ color: {c['text_disabled']}; background: {c['surface_disabled']}; }}
    QComboBox QAbstractItemView {{ color: {c['menu_text']}; background: {c['menu_background']}; selection-color: {c['selection_text']}; selection-background-color: {c['selection_background']}; border: 1px solid {c['border_default']}; outline: 0; }}
    QCheckBox, QRadioButton, QGroupBox {{ color: {c['text_primary']}; background: transparent; }}
    QCheckBox:disabled, QRadioButton:disabled {{ color: {c['text_disabled']}; }}
    QGroupBox {{ border: 1px solid {c['border_subtle']}; border-radius: 8px; margin-top: 12px; padding-top: 8px; }}
    QTableView, QTableWidget, QListView, QTreeView {{ font-family: "Tajawal"; color: {c['input_text']}; background: {c['surface_primary']}; alternate-background-color: {c['surface_secondary']}; border: 1px solid {c['border_default']}; border-radius: 10px; gridline-color: {c['border_subtle']}; selection-background-color: {c['selection_background']}; selection-color: {c['selection_text']}; }}
    QTableView::item:selected, QTableWidget::item:selected, QListView::item:selected, QTreeView::item:selected {{ color: {c['selection_text']}; background: {c['selection_background']}; }}
    QHeaderView, QHeaderView::section {{ font-family: "Tajawal"; color: {c['nav_text']}; background: {c['nav_background']}; border: none; padding: 9px; font-weight: 600; }}
    QMenu, QMenuBar {{ color: {c['menu_text']}; background: {c['menu_background']}; border: 1px solid {c['border_default']}; }}
    QMenu::item:selected, QMenuBar::item:selected {{ color: {c['selection_text']}; background: {c['selection_background']}; }}
    QMenu::item:disabled {{ color: {c['text_disabled']}; }}
    QToolTip {{ color: {c['tooltip_text']}; background: {c['tooltip_background']}; border: 1px solid {c['border_default']}; padding: 6px; }}
    QProgressBar {{ color: {c['text_primary']}; min-height: 14px; border: none; border-radius: 7px; background: {c['surface_secondary']}; text-align: center; }}
    QProgressBar::chunk {{ background: {c['primary']}; border-radius: 7px; }}
    QTabWidget::pane {{ border: 1px solid {c['border_subtle']}; background: {c['surface_primary']}; }}
    QTabBar::tab {{ color: {c['text_secondary']}; min-height: 36px; padding: 0 18px; background: {c['surface_secondary']}; }}
    QTabBar::tab:selected {{ background: {c['surface_primary']}; color: {c['primary']}; font-weight: 700; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical, QScrollBar:horizontal {{ background: {c['scrollbar_track']}; border: none; }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{ background: {c['scrollbar_handle']}; min-height: 24px; min-width: 24px; border-radius: 5px; }}
    QStatusBar {{ color: {c['text_secondary']}; background: {c['surface_primary']}; border-top: 1px solid {c['border_subtle']}; }}
    QFrame#dropZone {{ background: {c['surface_secondary']}; border: 2px dashed {c['border_default']}; border-radius: 12px; }}
    QFrame#dropZone[dragState="valid"] {{ border-color: {c['success']}; background: {c['success_background']}; }}
    QFrame#dropZone[dragState="invalid"] {{ border-color: {c['error']}; background: {c['error_background']}; }}
    QFrame#banner {{ background: {c['info_background']}; border: 1px solid {c['info']}; border-radius: 9px; }}
    QFrame#dialogPanel {{ background: {c['dialog_background']}; border: 1px solid {c['border_subtle']}; border-radius: 12px; }}
    """
