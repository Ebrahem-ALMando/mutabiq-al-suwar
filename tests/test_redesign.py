"""Regression checks for the official visual identity and interaction system."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableView

from ui.animations import AnimationManager
from ui.components.controls import ThemeToggle
from ui.icons import icon, logo_icon
from ui.models.result_model import ResultTableModel
from ui.pages.guide_page import GuidePage
from ui.pages.preview_page import PreviewPage
from ui.theme import PALETTES, stylesheet
from ui.tour import TourOverlay

ROOT = Path(__file__).resolve().parents[1]


def test_official_palette_tokens_are_exact() -> None:
    light = PALETTES["light"]
    dark = PALETTES["dark"]
    assert (light["background_primary"], light["primary"], light["gold"]) == (
        "#F8F6F2",
        "#054239",
        "#B5985A",
    )
    assert (dark["background_primary"], dark["primary"], dark["gold"]) == (
        "#032D23",
        "#8FC9BC",
        "#E2C992",
    )


def test_tajawal_is_explicit_for_app_and_tables() -> None:
    qss = stylesheet("light")
    assert 'font-family: "Tajawal"' in qss
    assert "QTableView" in qss and "QHeaderView" in qss


def test_local_icon_registry_and_official_logo_render() -> None:
    assert not icon("house", theme="light").pixmap(20, 20).isNull()
    assert not icon("unknown-name", theme="dark").pixmap(20, 20).isNull()
    assert not logo_icon().pixmap(64, 64).isNull()
    assert (ROOT / "assets/branding/official_logo.svg").is_file()
    assert (ROOT / "assets/branding/official_logo.png").is_file()
    assert (ROOT / "assets/icons/app.ico").is_file()


def test_visible_ui_sources_contain_no_emoji() -> None:
    emoji = re.compile("[\U0001f300-\U0001faff\u2600-\u26ff\u2700-\u27bf]")
    sources = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "ui").rglob("*.py"))
    assert not emoji.search(sources)


def test_preview_is_model_view_rtl_table_with_hidden_vertical_header(qtbot) -> None:
    page = PreviewPage()
    qtbot.addWidget(page)
    assert isinstance(page.table, QTableView)
    assert isinstance(page.model, ResultTableModel)
    assert page.table.verticalHeader().isHidden()
    assert page.model.HEADERS[0] == "صف Excel"
    assert page.table.textElideMode() == Qt.TextElideMode.ElideMiddle


def test_theme_toggle_is_accessible_and_reduced_motion_safe(qtbot) -> None:
    toggle = ThemeToggle("light", reduced_motion=True)
    qtbot.addWidget(toggle)
    with qtbot.waitSignal(toggle.themeChanged) as signal:
        qtbot.mouseClick(toggle, Qt.MouseButton.LeftButton)
    assert signal.args == ["dark"]
    assert toggle.accessibleName() == "تبديل السمة"
    assert toggle.get_position() == 1.0


def test_animation_manager_respects_reduced_motion(qtbot) -> None:
    page = PreviewPage()
    qtbot.addWidget(page)
    page.show()
    manager = AnimationManager(True)
    manager.fade_in(page)
    assert not manager._active


def test_guide_has_five_steps_and_twelve_local_illustrations(qtbot) -> None:
    guide = GuidePage(ROOT)
    qtbot.addWidget(guide)
    assert len(guide.STEPS) == 5
    assert len(list((ROOT / "assets/illustrations/guide").glob("*.svg"))) == 12


def test_tour_survives_missing_targets(qtbot) -> None:
    host = PreviewPage()
    qtbot.addWidget(host)
    host.resize(900, 600)
    host.show()
    tour = TourOverlay(host, [("missing-target", "عنصر اختياري")])
    qtbot.addWidget(tour)
    tour.show()
    tour.show_step(0)
    assert tour.target_rect.isNull()
