"""اختبارات فهرسة الصور والمطابقة الدقيقة."""

from services.image_matcher import ImageMatcher


def test_exact_stem_and_extensions_and_case_insensitive(tmp_path) -> None:
    (tmp_path / "a3222263.JPG").write_bytes(b"image")
    (tmp_path / "a32222630.jpg").write_bytes(b"image")
    (tmp_path / "a3222263_backup.png").write_bytes(b"image")
    (tmp_path / "ignore.txt").write_text("x")
    matcher = ImageMatcher()
    index, scanned = matcher.scan(tmp_path, False, True)
    assert scanned == 3
    assert [path.name for path in matcher.matches(index, "A3222263", True)] == ["a3222263.JPG"]


def test_multiple_source_matches_are_deterministic(tmp_path) -> None:
    (tmp_path / "person.png").write_bytes(b"png")
    (tmp_path / "person.jpg").write_bytes(b"jpg")
    index, _ = ImageMatcher().scan(tmp_path, False, True)
    names = [path.name for path in index["person"]]
    assert names == sorted(names, key=lambda name: (str(tmp_path / name).casefold(), str(tmp_path / name)))


def test_recursive_scanning_and_unicode_filename(tmp_path) -> None:
    nested = tmp_path / "صور" / "فرعي"
    nested.mkdir(parents=True)
    (nested / "رقم_١٢٣.webp").write_bytes(b"webp")
    matcher = ImageMatcher()
    flat, flat_count = matcher.scan(tmp_path, False, True)
    recursive, recursive_count = matcher.scan(tmp_path, True, True)
    assert flat_count == 0
    assert recursive_count == 1
    assert matcher.matches(recursive, "رقم_١٢٣", True)
    assert not flat


def test_destination_subfolder_can_be_excluded(tmp_path) -> None:
    destination = tmp_path / "output"
    destination.mkdir()
    (tmp_path / "source.jpg").write_bytes(b"source")
    (destination / "old.jpg").write_bytes(b"old")
    index, scanned = ImageMatcher().scan(tmp_path, True, True, excluded_folder=destination)
    assert scanned == 1
    assert "source" in index
    assert "old" not in index


def test_case_sensitive_option(tmp_path) -> None:
    (tmp_path / "AbC.jpeg").write_bytes(b"x")
    matcher = ImageMatcher()
    index, _ = matcher.scan(tmp_path, False, False)
    assert matcher.matches(index, "AbC", False)
    assert not matcher.matches(index, "abc", False)
