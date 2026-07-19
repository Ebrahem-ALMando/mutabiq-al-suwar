"""Helpers for stable Arabic UI with LTR file-system fragments."""

from __future__ import annotations

from pathlib import Path

LRI = "\u2066"
PDI = "\u2069"


def safe_path(value: str | Path, empty: str = "—") -> str:
    text = str(value).strip()
    return f"{LRI}{text}{PDI}" if text else empty


def elide_middle(value: str | Path, maximum: int = 58) -> str:
    text = str(value)
    if len(text) <= maximum:
        return safe_path(text)
    keep = max(8, (maximum - 1) // 2)
    return safe_path(f"{text[:keep]}…{text[-keep:]}")
