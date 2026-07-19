"""Compatibility import for integrations that used the original window module."""

from __future__ import annotations

import logging
from pathlib import Path

from ui.premium_window import MainWindow as PremiumMainWindow
from utils.app_paths import AppPaths


class MainWindow(PremiumMainWindow):
    """Forward the legacy constructor to the maintained production window."""

    def __init__(
        self,
        project_root: Path,
        app_paths: AppPaths | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(project_root, app_paths or AppPaths.create(), logger)
