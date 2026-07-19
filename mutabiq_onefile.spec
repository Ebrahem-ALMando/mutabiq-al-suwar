# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
documentation = ["README.md", "ARCHITECTURE.md", "USER_GUIDE_AR.md", "DEVELOPER_GUIDE.md", "CHANGELOG.md", "SECURITY.md", "PRIVACY.md", "THIRD_PARTY_NOTICES.md"]
datas = [(str(root / "assets"), "assets"), (str(root / "samples"), "samples")]
datas += [(str(root / name), ".") for name in documentation]
a = Analysis([str(root / "main.py")], pathex=[str(root)], binaries=[], datas=datas, hiddenimports=["openpyxl", "sqlite3", "PySide6.QtSvg"], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=["pytest", "black", "ruff", "mypy"], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="MutabiqAlSuwar-portable", debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=False, icon=str(root / "assets/icons/app.ico"), version=str(root / "packaging/version_info.txt"))
