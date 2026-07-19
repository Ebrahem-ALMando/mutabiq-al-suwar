"""فهرسة الصور ومطابقة أسماء الملفات بكفاءة."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from utils.constants import SUPPORTED_IMAGE_EXTENSIONS
from utils.path_helpers import is_path_within

ProgressCallback = Callable[[int, int, str], None]
CancelCallback = Callable[[], bool]


def match_key(value: str, case_insensitive: bool) -> str:
    """أنشئ مفتاح مطابقة من الساق الكاملة لاسم الملف."""

    return value.casefold() if case_insensitive else value


class ImageMatcher:
    """يفحص مجلد المصدر مرة واحدة ويبني فهرساً في الذاكرة."""

    def scan(
        self,
        source: Path,
        recursive: bool,
        case_insensitive: bool,
        excluded_folder: Path | None = None,
        progress: ProgressCallback | None = None,
        cancelled: CancelCallback | None = None,
        key_transform: Callable[[str], str] | None = None,
    ) -> tuple[dict[str, list[Path]], int]:
        """أعد فهرس الصور وعدد الملفات المدعومة المفحوصة."""

        if not source.is_dir():
            raise FileNotFoundError("مجلد الصور غير موجود.")
        iterator = source.rglob("*") if recursive else source.glob("*")
        index: dict[str, list[Path]] = defaultdict(list)
        scanned = 0
        for path in iterator:
            if cancelled and cancelled():
                break
            try:
                if not path.is_file():
                    continue
                if excluded_folder and is_path_within(path, excluded_folder):
                    continue
                if path.suffix.casefold() not in SUPPORTED_IMAGE_EXTENSIONS:
                    continue
                scanned += 1
                key = key_transform(path.stem) if key_transform else match_key(path.stem, case_insensitive)
                index[key].append(path)
                if progress and scanned % 25 == 0:
                    progress(scanned, 0, path.name)
            except OSError:
                continue
        deterministic = {
            key: sorted(paths, key=lambda item: (str(item).casefold(), str(item))) for key, paths in index.items()
        }
        if progress:
            progress(scanned, scanned, "")
        return deterministic, scanned

    @staticmethod
    def matches(index: dict[str, list[Path]], identifier: str, case_insensitive: bool) -> list[Path]:
        """أعد التطابقات ذات ساق اسم مساوية تماماً للمعرّف."""

        return list(index.get(match_key(identifier, case_insensitive), []))
