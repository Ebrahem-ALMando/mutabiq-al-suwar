"""مسارات بيانات التطبيق المحلية القابلة للحقن في الاختبارات."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppPaths:
    """مواقع البيانات التي لا ينبغي وضعها بجوار الملف التنفيذي."""

    root: Path
    database: Path
    logs: Path
    manifests: Path
    profiles: Path
    thumbnails: Path
    diagnostics: Path
    backups: Path

    @classmethod
    def create(cls, base: Path | None = None) -> AppPaths:
        """أنشئ بنية بيانات المستخدم وأعد مساراتها."""

        if base is None:
            local = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
            base = Path(local) / "MutabiqAlSuwar" if local else Path.home() / ".mutabiq_al_suwar"
        paths = cls(
            root=base,
            database=base / "data" / "mutabiq.db",
            logs=base / "logs",
            manifests=base / "manifests",
            profiles=base / "profiles",
            thumbnails=base / "thumbnails",
            diagnostics=base / "diagnostics",
            backups=base / "backups",
        )
        for folder in (
            paths.database.parent,
            paths.logs,
            paths.manifests,
            paths.profiles,
            paths.thumbnails,
            paths.diagnostics,
            paths.backups,
        ):
            folder.mkdir(parents=True, exist_ok=True)
        return paths
