"""تكامل SQLite والمنشور والتراجع الآمن."""

from models.result_models import ColumnInfo, JobResult, MatchStatus, ProcessingSettings, ProcessingStats, ResultRecord
from repositories.history_repository import HistoryRepository
from services.copy_service import CopyService
from services.manifest_service import ManifestService
from services.undo_service import UndoService


def make_result(tmp_path, history, manifests):
    source = tmp_path / "source" / "id.jpg"
    source.parent.mkdir()
    source.write_bytes(b"image-data")
    destination = tmp_path / "out"
    settings = ProcessingSettings(tmp_path / "data.xlsx", "Sheet", ColumnInfo(1, "ID", "A"), source.parent, destination)
    outcome = CopyService().copy_verified(source, destination, settings.duplicate_policy, verify_hash=True)
    record = ResultRecord(1, 2, "id", "id", MatchStatus.MATCHED, source_path=source, destination_path=outcome.target)
    record.copy_status = outcome.status
    record.source_size = outcome.source_size
    record.destination_size = outcome.destination_size
    record.destination_mtime_ns = outcome.destination_mtime_ns
    record.destination_sha256 = outcome.destination_sha256
    record.created_new_file = outcome.created_new_file
    record.verified = outcome.verified
    result = JobResult(
        settings,
        [record],
        ProcessingStats(
            valid_identifiers=1, matched_identifiers=1, copied_files=1, copied_bytes=outcome.destination_size
        ),
        finished_at="2026-01-01T00:00:01+00:00",
    )
    result.manifest_path = manifests.create(result)
    history.record_result(result)
    return result


def test_database_migration_history_manifest_and_safe_undo(tmp_path) -> None:
    history = HistoryRepository(tmp_path / "app.db")
    manifests = ManifestService(tmp_path / "manifests")
    result = make_result(tmp_path, history, manifests)
    assert history.dashboard()["batches"] == 1
    assert history.batch(result.batch_id)["copied_count"] == 1
    manifest, plan = UndoService(history).plan(result.manifest_path)
    assert manifest["batch_id"] == result.batch_id and len(plan) == 1 and plan[0].safe
    undo = UndoService(history).execute(result.manifest_path, confirmed=True)
    assert undo.status == "fully_undone"
    assert not result.records[0].destination_path.exists()


def test_undo_refuses_modified_destination(tmp_path) -> None:
    history = HistoryRepository(tmp_path / "app.db")
    manifests = ManifestService(tmp_path / "manifests")
    result = make_result(tmp_path, history, manifests)
    result.records[0].destination_path.write_bytes(b"changed")
    _, plan = UndoService(history).plan(result.manifest_path)
    assert not plan[0].safe
    undo = UndoService(history).execute(result.manifest_path, confirmed=True)
    assert undo.status == "undo_failed"
    assert result.records[0].destination_path.exists()


def test_incremental_index_removes_deleted_files(tmp_path) -> None:
    history = HistoryRepository(tmp_path / "app.db")
    source = tmp_path / "images"
    source.mkdir()
    image = source / "A.JPG"
    image.write_bytes(b"x")
    index, count = history.refresh_image_index(source, True, str.casefold)
    assert count == 1 and "a" in index
    image.unlink()
    index, count = history.refresh_image_index(source, True, str.casefold)
    assert count == 0 and not index
