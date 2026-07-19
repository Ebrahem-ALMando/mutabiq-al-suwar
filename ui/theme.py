"""Central semantic Qt palette and QSS generation for light and dark modes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QTableView

from ui.components.inputs import install_compound_input_style


@dataclass(frozen=True, slots=True)
class DesignTokens:
    spacing: tuple[int, ...] = (0, 4, 8, 12, 16, 20, 24, 32, 40, 48)
    radii: tuple[int, ...] = (4, 8, 12, 16, 24)
    animation_fast: int = 160
    animation_normal: int = 210
    animation_slow: int = 280
    input_height: int = 42
    button_height: int = 42
    table_row_height: int = 42
    sidebar_expanded: int = 252
    sidebar_collapsed: int = 76


TOKENS = DesignTokens()

PALETTES: dict[str, dict[str, str]] = {
    "light": {
        "background_primary": "#F8F6F2",
        "background_secondary": "#F0EDE7",
        "surface_primary": "#FFFFFF",
        "surface_secondary": "#F0EDE7",
        "surface_elevated": "#FFFFFF",
        "surface_hover": "#E8E4DC",
        "surface_pressed": "#DED9D0",
        "surface_selected": "#E1ECE9",
        "surface_disabled": "#E8E4DC",
        "text_primary": "#2D3A38",
        "text_secondary": "#465552",
        "text_muted": "#6B7876",
        "text_disabled": "#7B8784",
        "text_on_primary": "#FFFFFF",
        "text_on_success": "#FFFFFF",
        "text_on_warning": "#FFFFFF",
        "text_on_error": "#FFFFFF",
        "text_on_gold": "#2D3A38",
        "border_default": "#DED9D0",
        "border_subtle": "#E8E4DC",
        "border_focus": "#054239",
        "primary": "#054239",
        "primary_hover": "#0A5548",
        "primary_pressed": "#032D23",
        "gold": "#B5985A",
        "gold_muted": "#9A8255",
        "secondary": "#F0EDE7",
        "muted": "#E8E4DC",
        "success": "#167052",
        "success_background": "#E0F1EB",
        "warning": "#8A641D",
        "warning_background": "#F7EDD7",
        "error": "#C53030",
        "error_background": "#FCE5E5",
        "info": "#075E52",
        "info_background": "#E1ECE9",
        "selection_background": "#054239",
        "selection_text": "#FFFFFF",
        "input_background": "#FFFFFF",
        "input_text": "#2D3A38",
        "input_placeholder": "#6B7876",
        "tooltip_background": "#032D23",
        "tooltip_text": "#FFFFFF",
        "menu_background": "#FFFFFF",
        "menu_text": "#2D3A38",
        "dialog_background": "#FFFFFF",
        "dialog_text": "#2D3A38",
        "overlay_background": "#2D3A38",
        "scrollbar_track": "#F0EDE7",
        "scrollbar_handle": "#9CABA6",
        "nav_background": "#054239",
        "nav_text": "#F8F6F2",
    },
    "dark": {
        "background_primary": "#032D23",
        "background_secondary": "#054239",
        "surface_primary": "#054239",
        "surface_secondary": "#0A4A3E",
        "surface_elevated": "#0A4A3E",
        "surface_hover": "#0F5C4D",
        "surface_pressed": "#146B5A",
        "surface_selected": "#0F5C4D",
        "surface_disabled": "#0A4A3E",
        "text_primary": "#E8EBE9",
        "text_secondary": "#CBD2CF",
        "text_muted": "#9CABA6",
        "text_disabled": "#84958F",
        "text_on_primary": "#032D23",
        "text_on_success": "#032D23",
        "text_on_warning": "#032D23",
        "text_on_error": "#032D23",
        "text_on_gold": "#032D23",
        "border_default": "#0F5C4D",
        "border_subtle": "#0A4A3E",
        "border_focus": "#E2C992",
        "primary": "#8FC9BC",
        "primary_hover": "#A8D6CC",
        "primary_pressed": "#75B5A7",
        "gold": "#E2C992",
        "gold_muted": "#D4B87A",
        "secondary": "#0A4A3E",
        "muted": "#0F5C4D",
        "success": "#8FC9BC",
        "success_background": "#0A4A3E",
        "warning": "#E2C992",
        "warning_background": "#4A4025",
        "error": "#F87171",
        "error_background": "#552B2B",
        "info": "#8FC9BC",
        "info_background": "#0A4A3E",
        "selection_background": "#8FC9BC",
        "selection_text": "#032D23",
        "input_background": "#032D23",
        "input_text": "#E8EBE9",
        "input_placeholder": "#9CABA6",
        "tooltip_background": "#E8EBE9",
        "tooltip_text": "#032D23",
        "menu_background": "#0A4A3E",
        "menu_text": "#E8EBE9",
        "dialog_background": "#054239",
        "dialog_text": "#E8EBE9",
        "overlay_background": "#021B15",
        "scrollbar_track": "#032D23",
        "scrollbar_handle": "#3C796D",
        "nav_background": "#032D23",
        "nav_text": "#E8EBE9",
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
        QPalette.ColorRole.Window: "background_primary",
        QPalette.ColorRole.WindowText: "text_primary",
        QPalette.ColorRole.Base: "input_background",
        QPalette.ColorRole.AlternateBase: "surface_secondary",
        QPalette.ColorRole.ToolTipBase: "tooltip_background",
        QPalette.ColorRole.ToolTipText: "tooltip_text",
        QPalette.ColorRole.Text: "input_text",
        QPalette.ColorRole.Button: "surface_primary",
        QPalette.ColorRole.ButtonText: "text_primary",
        QPalette.ColorRole.Highlight: "selection_background",
        QPalette.ColorRole.HighlightedText: "selection_text",
        QPalette.ColorRole.PlaceholderText: "input_placeholder",
        QPalette.ColorRole.Link: "info",
    }
    for role, token in roles.items():
        palette.setColor(QPalette.ColorGroup.All, role, QColor(c[token]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(c["text_disabled"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(c["text_disabled"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(c["text_disabled"]))
    return palette


def apply_application_theme(
    app: QApplication, theme: str, large_text: bool = False, high_contrast: bool = False
) -> None:
    install_compound_input_style(app)
    app.setProperty("active_theme", theme)
    app.setProperty("high_contrast", high_contrast)
    app.setPalette(qt_palette(theme, high_contrast))
    app.setStyleSheet(stylesheet(theme, large_text, high_contrast))
    for widget in app.topLevelWidgets():
        widget.setPalette(app.palette())
        for table in widget.findChildren(QTableView):
            table.setFont(QFont("Tajawal", table.font().pointSize()))
            table.horizontalHeader().setFont(QFont("Tajawal", table.font().pointSize()))
            table.verticalHeader().setFont(QFont("Tajawal", table.font().pointSize()))
            table.verticalHeader().hide()
            table.verticalHeader().setDefaultSectionSize(TOKENS.table_row_height)
            table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()


def stylesheet(theme: str = "light", large_text: bool = False, high_contrast: bool = False) -> str:
    c = colors_for(theme, high_contrast)
    size = 14 if large_text else 13
    controls = Path(__file__).resolve().parents[1] / "assets" / "icons" / "controls"
    arrow_variant = "dark" if theme == "dark" else "light"
    arrow_up = (controls / f"chevron-up-{arrow_variant}.svg").as_posix()
    arrow_down = (controls / f"chevron-down-{arrow_variant}.svg").as_posix()
    return f"""
    * {{ font-family: "Tajawal", "Segoe UI", Arial; font-size: {size}px; }}
    QMainWindow, QWidget#appRoot {{ background: {c['background_primary']}; color: {c['text_primary']}; }}
    QWidget {{ color: {c['text_primary']}; }}
    QDialog, QMessageBox {{ background: {c['dialog_background']}; color: {c['dialog_text']}; }}
    QDialog QLabel, QMessageBox QLabel {{ background: transparent; color: {c['dialog_text']}; }}
    QFrame#sidebar {{ background: {c['nav_background']}; border: none; }}
    QFrame#topbar, QFrame#card {{ background: {c['surface_primary']}; border: 1px solid {c['border_default']}; border-radius: 12px; }}
    QFrame#hero {{ background: {c['primary']}; border: 1px solid {c['gold_muted']}; border-radius: 16px; }}
    QFrame#hero QLabel, QFrame#hero QLabel#sectionTitle, QFrame#hero QLabel#pageDescription {{ color: {c['text_on_primary']}; }}
    QFrame#hero QLabel#eyebrow {{ color: {c['gold']}; }}
    QFrame#segmented {{ background: {c['secondary']}; border: 1px solid {c['border_default']}; border-radius: 10px; }}
    QLabel {{ color: {c['text_primary']}; background: transparent; }}
    QLabel#productName {{ color: {c['nav_text']}; font-size: 18px; font-weight: 700; }}
    QLabel#pageTitle {{ color: {c['text_primary']}; font-size: 23px; font-weight: 700; }}
    QLabel#pageDescription, QLabel#muted {{ color: {c['text_muted']}; }}
    QLabel#sectionTitle {{ color: {c['text_primary']}; font-size: 16px; font-weight: 600; }}
    QLabel#statValue {{ color: {c['primary']}; font-size: 24px; font-weight: 700; }}
    QLabel#emptyTitle {{ color: {c['text_primary']}; font-size: 17px; font-weight: 700; }}
    QLabel#eyebrow {{ color: {c['gold_muted']}; font-size: 12px; font-weight: 700; }}
    QLabel[severity="success"], QLabel#sectionTitle[severity="success"] {{ color: {c['success']}; }}
    QLabel[severity="warning"], QLabel#sectionTitle[severity="warning"] {{ color: {c['warning']}; }}
    QLabel[severity="error"], QLabel#sectionTitle[severity="error"] {{ color: {c['error']}; }}
    QPushButton, QToolButton {{ color: {c['text_primary']}; min-height: {TOKENS.button_height}px; padding: 0 14px; border-radius: 8px; border: 1px solid {c['border_default']}; background: {c['surface_primary']}; }}
    QPushButton:hover, QToolButton:hover {{ background: {c['surface_hover']}; border-color: {c['primary']}; }}
    QPushButton:pressed, QToolButton:pressed {{ background: {c['surface_pressed']}; }}
    QPushButton:focus, QToolButton:focus {{ border: 2px solid {c['border_focus']}; }}
    QPushButton:disabled, QToolButton:disabled {{ color: {c['text_disabled']}; background: {c['surface_disabled']}; border-color: {c['border_subtle']}; }}
    QPushButton#primary {{ color: {c['text_on_primary']}; border-color: {c['primary']}; background: {c['primary']}; font-weight: 700; }}
    QPushButton#primary:hover {{ background: {c['primary_hover']}; }} QPushButton#primary:pressed {{ background: {c['primary_pressed']}; }}
    QPushButton#heroPrimary {{ color: {c['text_on_gold']}; background: {c['gold']}; border-color: {c['gold']}; font-weight: 700; }}
    QPushButton#heroPrimary:hover {{ background: {c['gold_muted']}; border-color: {c['gold_muted']}; }}
    QPushButton[severity="error"] {{ color: {c['text_on_error']}; background: {c['error']}; border-color: {c['error']}; font-weight: 700; }}
    QToolButton#mainMenuButton, QPushButton#helpButton {{ min-width: 42px; max-width: 42px; min-height: 42px; max-height: 42px; padding: 0; }}
    QPushButton#notificationButton {{ min-width: 42px; max-width: 72px; min-height: 42px; max-height: 42px; padding: 0 8px; }}
    QToolButton#mainMenuButton::menu-indicator {{ image: none; width: 0; height: 0; }}
    QPushButton#segmentButton {{ min-height: 34px; border: none; background: transparent; padding: 0 12px; }}
    QPushButton#segmentButton:checked {{ color: {c['primary']}; background: {c['surface_primary']}; border: 1px solid {c['border_default']}; font-weight: 700; }}
    QPushButton#wizardStep {{ min-height: 44px; color: {c['text_secondary']}; background: transparent; border: none; border-bottom: 3px solid {c['border_default']}; border-radius: 0; }}
    QPushButton#wizardStep[current="true"] {{ color: {c['primary']}; border-bottom-color: {c['gold']}; font-weight: 700; }}
    QPushButton#wizardStep[complete="true"] {{ color: {c['primary']}; border-bottom-color: {c['primary']}; }}
    QLineEdit, QTextEdit, QPlainTextEdit {{ color: {c['input_text']}; background: {c['input_background']}; selection-color: {c['selection_text']}; selection-background-color: {c['selection_background']}; min-height: {TOKENS.input_height}px; border: 1px solid {c['border_default']}; border-radius: 8px; padding: 0 10px; }}
    QComboBox {{ color: {c['input_text']}; background: {c['input_background']}; selection-color: {c['selection_text']}; selection-background-color: {c['selection_background']}; min-height: 42px; border: 1px solid {c['border_default']}; border-radius: 8px; padding: 0 10px 0 42px; }}
    QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit {{ color: {c['input_text']}; background: {c['input_background']}; selection-color: {c['selection_text']}; selection-background-color: {c['selection_background']}; min-height: 42px; border: 1px solid {c['border_default']}; border-radius: 8px; padding: 0 40px 0 10px; }}
    QComboBox::drop-down {{ subcontrol-origin: border; subcontrol-position: center left; width: 36px; border: none; border-right: 1px solid {c['border_default']}; border-top-left-radius: 7px; border-bottom-left-radius: 7px; background: {c['surface_secondary']}; }}
    QComboBox::down-arrow {{ image: url("{arrow_down}"); width: 14px; height: 14px; }}
    QSpinBox::up-button, QDoubleSpinBox::up-button, QDateEdit::up-button, QTimeEdit::up-button, QDateTimeEdit::up-button {{ subcontrol-origin: border; subcontrol-position: top right; width: 32px; height: 20px; border: none; border-left: 1px solid {c['border_default']}; border-bottom: 1px solid {c['border_default']}; border-top-right-radius: 7px; background: {c['surface_secondary']}; }}
    QSpinBox::down-button, QDoubleSpinBox::down-button, QDateEdit::down-button, QTimeEdit::down-button, QDateTimeEdit::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; width: 32px; height: 20px; border: none; border-left: 1px solid {c['border_default']}; border-bottom-right-radius: 7px; background: {c['surface_secondary']}; }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow, QDateEdit::up-arrow, QTimeEdit::up-arrow, QDateTimeEdit::up-arrow {{ image: url("{arrow_up}"); width: 12px; height: 12px; }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QDateEdit::down-arrow, QTimeEdit::down-arrow, QDateTimeEdit::down-arrow {{ image: url("{arrow_down}"); width: 12px; height: 12px; }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus {{ border: 2px solid {c['border_focus']}; }}
    QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled, QTimeEdit:disabled, QDateTimeEdit:disabled {{ color: {c['text_disabled']}; background: {c['surface_disabled']}; }}
    QComboBox QAbstractItemView {{ color: {c['menu_text']}; background: {c['menu_background']}; selection-color: {c['selection_text']}; selection-background-color: {c['selection_background']}; border: 1px solid {c['border_default']}; outline: 0; }}
    QCheckBox, QRadioButton, QGroupBox {{ color: {c['text_primary']}; background: transparent; spacing: 8px; }}
    QCheckBox::indicator, QRadioButton::indicator {{ width: 18px; height: 18px; border: 2px solid {c['border_default']}; background: {c['input_background']}; }}
    QCheckBox::indicator {{ border-radius: 5px; }} QRadioButton::indicator {{ border-radius: 10px; }}
    QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {c['primary']}; }}
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{ background: {c['primary']}; border-color: {c['primary']}; }}
    QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{ background: {c['surface_disabled']}; border-color: {c['border_subtle']}; }}
    QCheckBox:disabled, QRadioButton:disabled {{ color: {c['text_disabled']}; }}
    QGroupBox {{ border: 1px solid {c['border_subtle']}; border-radius: 8px; margin-top: 12px; padding-top: 8px; }}
    QTableView, QTableWidget, QListView, QTreeView {{ font-family: "Tajawal"; color: {c['input_text']}; background: {c['surface_primary']}; alternate-background-color: {c['surface_secondary']}; border: 1px solid {c['border_default']}; border-radius: 10px; gridline-color: {c['border_subtle']}; selection-background-color: {c['selection_background']}; selection-color: {c['selection_text']}; }}
    QTableView::item:selected, QTableWidget::item:selected, QListView::item:selected, QTreeView::item:selected {{ color: {c['selection_text']}; background: {c['selection_background']}; }}
    QHeaderView, QHeaderView::section {{ font-family: "Tajawal"; color: {c['nav_text']}; background: {c['nav_background']}; border: none; min-height: 40px; padding: 4px 9px; font-weight: 600; }}
    QMenu, QMenuBar {{ color: {c['menu_text']}; background: {c['menu_background']}; border: 1px solid {c['border_default']}; }}
    QMenu::item:selected, QMenuBar::item:selected {{ color: {c['selection_text']}; background: {c['selection_background']}; }}
    QMenu::item:disabled {{ color: {c['text_disabled']}; }}
    QToolTip {{ color: {c['tooltip_text']}; background: {c['tooltip_background']}; border: 1px solid {c['border_default']}; padding: 6px; }}
    QProgressBar {{ color: {c['text_primary']}; min-height: 18px; border: 1px solid {c['border_default']}; border-radius: 9px; background: {c['surface_secondary']}; text-align: center; }}
    QProgressBar::chunk {{ background: {c['primary']}; border-radius: 8px; }}
    QTabWidget::pane {{ border: 1px solid {c['border_subtle']}; background: {c['surface_primary']}; }}
    QTabBar::tab {{ color: {c['text_secondary']}; min-height: 36px; padding: 0 18px; background: {c['surface_secondary']}; }}
    QTabBar::tab:selected {{ background: {c['surface_primary']}; color: {c['primary']}; font-weight: 700; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ background: {c['scrollbar_track']}; width: 12px; margin: 2px; border: none; }}
    QScrollBar:horizontal {{ background: {c['scrollbar_track']}; height: 12px; margin: 2px; border: none; }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{ background: {c['scrollbar_handle']}; min-height: 28px; min-width: 28px; border-radius: 5px; }}
    QScrollBar::handle:hover {{ background: {c['primary']}; }}
    QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; border: none; width: 0; height: 0; }}
    QStatusBar {{ color: {c['text_secondary']}; background: {c['surface_primary']}; border-top: 1px solid {c['border_subtle']}; }}
    QFrame#dropZone {{ background: {c['surface_secondary']}; border: 2px dashed {c['border_default']}; border-radius: 12px; }}
    QFrame#dropZone[dragState="valid"] {{ border-color: {c['success']}; background: {c['success_background']}; }}
    QFrame#dropZone[dragState="invalid"] {{ border-color: {c['error']}; background: {c['error_background']}; }}
    QFrame#banner {{ background: {c['info_background']}; border: 1px solid {c['info']}; border-radius: 9px; }}
    QFrame#dialogPanel {{ background: {c['dialog_background']}; border: 1px solid {c['border_subtle']}; border-radius: 12px; }}
    """
