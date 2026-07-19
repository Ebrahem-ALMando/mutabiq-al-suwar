"""حفظ ملفات تعريف المطابقة كـ JSON بيانات فقط."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from utils.version import PROFILE_SCHEMA_VERSION


class ProfileService:
    """CRUD آمن لملفات تعريف ذات مخطط ذي إصدار."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)

    def list_profiles(self) -> list[dict]:
        profiles: list[dict] = []
        for path in sorted(self.directory.glob("*.json"), key=lambda item: item.name.casefold()):
            try:
                profiles.append(self.load(path))
            except (ValueError, OSError, json.JSONDecodeError):
                continue
        return profiles

    def validate(self, data: dict) -> list[str]:
        errors: list[str] = []
        if data.get("schema_version") != PROFILE_SCHEMA_VERSION:
            errors.append("إصدار ملف التعريف غير مدعوم.")
        if not isinstance(data.get("name"), str) or not data["name"].strip():
            errors.append("اسم ملف التعريف مطلوب.")
        if data.get("matching_mode", "exact") not in {"exact", "normalized", "pattern", "fuzzy"}:
            errors.append("نمط المطابقة غير صالح.")
        rules = data.get("transformation_rules", [])
        if not isinstance(rules, list) or any(not isinstance(rule, dict) for rule in rules):
            errors.append("قواعد التحويل غير صالحة.")
        return errors

    def save(self, name: str, settings: dict) -> Path:
        data = {
            "schema_version": PROFILE_SCHEMA_VERSION,
            "name": name.strip(),
            **settings,
        }
        errors = self.validate(data)
        if errors:
            raise ValueError(" ".join(errors))
        safe_name = re_safe_name(name)
        path = self.directory / f"{safe_name}.json"
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return path

    def load(self, path: Path) -> dict:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("ملف التعريف يجب أن يحتوي كائناً JSON.")
        errors = self.validate(data)
        if errors:
            raise ValueError(" ".join(errors))
        return data

    def delete(self, path: Path) -> None:
        resolved = path.resolve()
        resolved.relative_to(self.directory.resolve())
        resolved.unlink(missing_ok=True)


def re_safe_name(name: str) -> str:
    """اسم ملف محدود من اسم ملف التعريف."""

    return (
        "".join(character if character.isalnum() or character in "-_ " else "_" for character in name).strip()[:80]
        or "profile"
    )
