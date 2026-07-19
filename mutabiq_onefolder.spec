# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
a = Analysis([str(root / "main.py")], pathex=[str(root)], binaries=[], datas=[(str(root / "assets"), "assets")], hiddenimports=["openpyxl", "sqlite3", "PySide6.QtSvg"], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=["pytest", "black", "ruff", "mypy"], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="MutabiqAlSuwar", debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=False, icon=str(root / "assets/icons/app.ico"), version=str(root / "packaging/version_info.txt"))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, upx_exclude=[], name="MutabiqAlSuwar")

