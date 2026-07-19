"""اختبارات GUI مركزة عبر pytest-qt."""

from models.result_models import MatchStatus, ResultRecord
from ui.models.result_model import ResultFilterProxy, ResultTableModel
from ui.pages.operation_page import OperationPage
from ui.theme import stylesheet


def test_wizard_requires_inputs_and_copy_requires_preview(qtbot) -> None:
    page = OperationPage()
    qtbot.addWidget(page)
    assert page._step_error(0)
    assert not page.copy_button.isEnabled()
    page.go_to(4)
    assert not page.copy_button.isEnabled()


def test_theme_styles_are_distinct() -> None:
    assert stylesheet("light") != stylesheet("dark")
    assert "#032D23" in stylesheet("dark")


def test_result_proxy_filters_status(qtbot) -> None:
    model = ResultTableModel()
    model.set_records(
        [ResultRecord(1, 2, "A", "A", MatchStatus.MATCHED), ResultRecord(2, 3, "B", "B", MatchStatus.NOT_FOUND)]
    )
    proxy = ResultFilterProxy()
    proxy.setSourceModel(model)
    proxy.set_status("matched")
    assert proxy.rowCount() == 1
    proxy.set_search("B")
    assert proxy.rowCount() == 0
