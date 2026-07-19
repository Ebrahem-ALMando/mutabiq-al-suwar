"""اختبارات سياسات تعارض ملفات الوجهة."""

from models.result_models import CopyStatus, DuplicatePolicy
from services.copy_service import CopyService


def test_copy_new_file(tmp_path) -> None:
    source = tmp_path / "source" / "id.jpg"
    source.parent.mkdir()
    source.write_bytes(b"new")
    destination = tmp_path / "destination"
    status, target, _ = CopyService().copy(source, destination, DuplicatePolicy.SKIP)
    assert status == CopyStatus.COPIED
    assert target.read_bytes() == b"new"


def test_skip_existing_file(tmp_path) -> None:
    source = tmp_path / "source" / "id.jpg"
    destination = tmp_path / "destination"
    source.parent.mkdir()
    destination.mkdir()
    source.write_bytes(b"new")
    (destination / "id.jpg").write_bytes(b"old")
    status, target, _ = CopyService().copy(source, destination, DuplicatePolicy.SKIP)
    assert status == CopyStatus.SKIPPED
    assert target.read_bytes() == b"old"


def test_overwrite_existing_file(tmp_path) -> None:
    source = tmp_path / "source" / "id.jpg"
    destination = tmp_path / "destination"
    source.parent.mkdir()
    destination.mkdir()
    source.write_bytes(b"new")
    (destination / "id.jpg").write_bytes(b"old")
    status, target, _ = CopyService().copy(source, destination, DuplicatePolicy.OVERWRITE)
    assert status == CopyStatus.COPIED
    assert target.read_bytes() == b"new"


def test_automatic_renaming_never_overwrites(tmp_path) -> None:
    source = tmp_path / "source" / "id.jpg"
    destination = tmp_path / "destination"
    source.parent.mkdir()
    destination.mkdir()
    source.write_bytes(b"new")
    (destination / "id.jpg").write_bytes(b"one")
    (destination / "id_2.jpg").write_bytes(b"two")
    status, target, _ = CopyService().copy(source, destination, DuplicatePolicy.RENAME)
    assert status == CopyStatus.RENAMED
    assert target.name == "id_3.jpg"
    assert target.read_bytes() == b"new"
