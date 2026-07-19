"""Targeted regressions for the 2.1.1 icon, sidebar, and compound-input fixes."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QEnterEvent
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QComboBox, QDateEdit, QStyle, QStyleOptionComplex

from ui.components.inputs import NumericDoubleSpinBox, NumericSpinBox, spin_subcontrol_rects
from ui.components.sidebar import Sidebar, SidebarNavItem
from ui.icons import icon_names, icon_pixmap, svg_metadata
from ui.theme import apply_application_theme
from utils.contrast import contrast_ratio

ROOT = Path(__file__).resolve().parents[1]
SIZES = (16, 20, 22, 24, 32)
RATIOS = (1.0, 1.25, 1.5, 1.75, 2.0)


def _alpha_bounds(pixmap):
    image = pixmap.toImage()
    points = [(x, y) for y in range(image.height()) for x in range(image.width()) if image.pixelColor(x, y).alpha() > 0]
    assert points
    xs, ys = zip(*points, strict=True)
    return min(xs), min(ys), max(xs), max(ys), image.width(), image.height()


@pytest.mark.parametrize("name", icon_names())
def test_every_svg_is_valid_and_has_nonempty_viewbox(name: str) -> None:
    metadata = svg_metadata(name)
    assert metadata.valid
    assert not metadata.view_box.isEmpty()
    assert metadata.view_box.width() > 0 and metadata.view_box.height() > 0


def test_every_bundled_svg_loads_with_a_complete_viewbox() -> None:
    for path in (ROOT / "assets").rglob("*.svg"):
        renderer = QSvgRenderer(str(path))
        assert renderer.isValid(), path
        view_box = renderer.viewBoxF()
        assert not view_box.isEmpty(), path
        assert view_box.left() >= 0 and view_box.top() >= 0, path


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("ratio", RATIOS)
def test_every_icon_has_safe_transparent_boundary(size: int, ratio: float, qapp: QApplication) -> None:
    del qapp
    for name in icon_names():
        left, top, right, bottom, width, height = _alpha_bounds(
            icon_pixmap(name, color="#054239", size=size, ratio=ratio)
        )
        assert left > 0 and top > 0, name
        assert right < width - 1 and bottom < height - 1, name


def test_official_logo_bytes_are_unchanged() -> None:
    png = ROOT / "assets/branding/official_logo.png"
    svg = ROOT / "assets/branding/official_logo.svg"
    assert hashlib.sha256(png.read_bytes()).hexdigest().upper() == (
        "B11D9307E980EFBD924C8FC610EBBDFE98E83940E4FDE07AB4E1651E0F15C82A"
    )
    assert hashlib.sha256(svg.read_bytes()).hexdigest().upper() == (
        "106DFB9C608C97DF4AE36DF51CA0C009BD1923CE1354748D115FDCB893853D82"
    )


def test_sidebar_is_one_explicit_rtl_component_family(qtbot) -> None:
    sidebar = Sidebar(str(ROOT / "assets/branding/official_logo.png"), reduced_motion=True)
    qtbot.addWidget(sidebar)
    sidebar.resize(250, 700)
    sidebar.show()
    assert sidebar.layoutDirection() == Qt.LayoutDirection.RightToLeft
    assert all(type(button) is SidebarNavItem for button in sidebar.buttons.values())
    for button in sidebar.buttons.values():
        assert button.layoutDirection() == Qt.LayoutDirection.RightToLeft
        rects = button.content_rects()
        assert rects["icon"].left() > rects["text"].right()
        assert rects["icon"].width() == rects["icon"].height() == 28


def test_operation_full_row_hover_active_focus_and_collapse(qtbot) -> None:
    item = SidebarNavItem("عملية جديدة", "plus")
    qtbot.addWidget(item)
    item.set_reduced_motion(True)
    item.resize(260, 48)
    item.show()
    qtbot.waitExposed(item)

    rects = item.content_rects()
    icon_point = QPointF(rects["icon"].center())
    QApplication.sendEvent(item, QEnterEvent(icon_point, icon_point, icon_point))
    assert item.property("hovered") is True
    item._animate_hover(0.0)
    text_point = QPointF(rects["text"].center())
    QApplication.sendEvent(item, QEnterEvent(text_point, text_point, text_point))
    assert item.property("hovered") is True

    item.set_hover_progress(0.0)
    hover = item.resolved_state_colors()
    item.set_hover_progress(1.0)
    hovered = item.resolved_state_colors()
    assert hover["background"] != hovered["background"]

    item.setChecked(True)
    active_hover = item.resolved_state_colors()
    assert active_hover["background"] != hovered["background"]
    assert active_hover["indicator"].isValid()
    item.activateWindow()
    item.setFocus(Qt.FocusReason.TabFocusReason)
    QApplication.processEvents()
    assert item.hasFocus()
    assert item.property("keyboardFocused") is True

    item.set_collapsed(True)
    item.resize(76, 48)
    icon_rect = item.content_rects()["icon"]
    assert item.rect().contains(icon_rect)
    assert item.content_rects()["text"].isNull()


@pytest.mark.parametrize("theme", ("light", "dark"))
def test_active_sidebar_icon_contrast(theme: str, qtbot) -> None:
    item = SidebarNavItem("الرئيسية", "house")
    qtbot.addWidget(item)
    item.set_theme(theme)
    item.setChecked(True)
    colors = item.resolved_state_colors()
    assert colors["icon"].name().lower() != "#ffffff"
    assert contrast_ratio(colors["icon"].name(), colors["background"].name()) >= 4.5


@pytest.mark.parametrize("widget_type", (NumericSpinBox, NumericDoubleSpinBox, QDateEdit))
def test_compound_spin_rectangles_never_intersect(widget_type, qtbot) -> None:
    widget = widget_type()
    qtbot.addWidget(widget)
    widget.resize(150, 44)
    widget.show()
    rects = spin_subcontrol_rects(widget)
    assert not rects["editor"].intersects(rects["up"])
    assert not rects["editor"].intersects(rects["down"])
    assert not rects["up"].intersects(rects["down"])
    assert widget.lineEdit().layoutDirection() == Qt.LayoutDirection.LeftToRight


@pytest.mark.parametrize("value", (0.0, 0.82, 1.0, 100.0, -25.0, 999999.0))
def test_numeric_values_prefix_suffix_and_controls_remain_separate(value: float, qtbot) -> None:
    field = NumericDoubleSpinBox()
    qtbot.addWidget(field)
    field.setRange(-999999, 999999)
    field.setDecimals(2)
    field.setPrefix("ID ")
    field.setSuffix(" %")
    field.setValue(value)
    field.resize(150, 44)
    field.show()
    rects = spin_subcontrol_rects(field)
    editor = field.lineEdit().geometry()
    assert field.minimumWidth() >= 140 and field.minimumHeight() >= 44
    assert not editor.intersects(rects["up"])
    assert not editor.intersects(rects["down"])
    assert field.lineEdit().text()


def test_rtl_combo_and_date_subcontrols_reserve_text_space(qtbot) -> None:
    apply_application_theme(QApplication.instance(), "light")
    combo = QComboBox()
    qtbot.addWidget(combo)
    combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    combo.addItem("قيمة طويلة لا تتداخل مع السهم")
    combo.resize(180, 44)
    combo.show()
    option = QStyleOptionComplex()
    option.initFrom(combo)
    option.rect = combo.rect()
    arrow = combo.style().subControlRect(
        QStyle.ComplexControl.CC_ComboBox,
        option,
        QStyle.SubControl.SC_ComboBoxArrow,
        combo,
    )
    edit = combo.style().subControlRect(
        QStyle.ComplexControl.CC_ComboBox,
        option,
        QStyle.SubControl.SC_ComboBoxEditField,
        combo,
    )
    assert not arrow.intersects(edit)
    assert arrow.left() < edit.left()


def test_top_level_theme_install_keeps_compound_style_once(qapp: QApplication) -> None:
    apply_application_theme(qapp, "light")
    installed = qapp._mutabiq_compound_style  # type: ignore[attr-defined]
    apply_application_theme(qapp, "dark")
    assert qapp._mutabiq_compound_style is installed  # type: ignore[attr-defined]


@pytest.mark.parametrize("ratio", RATIOS)
def test_numeric_geometry_in_real_scaled_qt_process(ratio: float) -> None:
    script = textwrap.dedent(
        """
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        from ui.components.inputs import NumericDoubleSpinBox, NumericSpinBox, spin_subcontrol_rects
        from ui.theme import apply_application_theme

        app = QApplication([])
        apply_application_theme(app, "light")
        for field_type, value in ((NumericSpinBox, -25), (NumericDoubleSpinBox, 0.82)):
            field = field_type()
            field.setRange(-999999, 999999)
            field.setValue(value)
            field.resize(150, 44)
            field.show()
            app.processEvents()
            rects = spin_subcontrol_rects(field)
            assert not rects["editor"].intersects(rects["up"])
            assert not rects["editor"].intersects(rects["down"])
            assert not rects["up"].intersects(rects["down"])
            assert not field.lineEdit().geometry().intersects(rects["up"])
            assert not field.lineEdit().geometry().intersects(rects["down"])
            assert field.lineEdit().layoutDirection() == Qt.LayoutDirection.LeftToRight
        """
    )
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["QT_SCALE_FACTOR"] = str(ratio)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
