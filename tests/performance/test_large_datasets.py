"""اختبارات أداء اصطناعية؛ تُشغل صراحة عبر RUN_PERFORMANCE_TESTS=1."""

import os
import time
from pathlib import Path

import pytest

from models.result_models import ColumnInfo, ProcessingSettings
from services.matching_service import SmartMatchingEngine

pytestmark = [
    pytest.mark.performance,
    pytest.mark.skipif(os.environ.get("RUN_PERFORMANCE_TESTS") != "1", reason="performance suite is opt-in"),
]


@pytest.mark.parametrize("count", [10_000, 100_000])
def test_exact_lookup_scale(tmp_path, count) -> None:
    index = {f"id{number:06}": [Path(f"id{number:06}.jpg")] for number in range(count)}
    settings = ProcessingSettings(tmp_path / "x.xlsx", "Sheet", ColumnInfo(1, "ID", "A"), tmp_path, tmp_path / "out")
    engine = SmartMatchingEngine()
    started = time.perf_counter()
    found = sum(engine.identifier_key(f"ID{number:06}", settings) in index for number in range(count))
    elapsed = time.perf_counter() - started
    assert found == count
    assert elapsed < 10.0
