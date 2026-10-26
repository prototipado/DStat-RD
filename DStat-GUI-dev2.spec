# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

project_root = SPECPATH
hiddenimports = [
    "PyQt6.sip",
    "serial.tools.list_ports",
    "serial.tools.list_ports_windows",
    "matplotlib.backends.backend_qtagg",
]
datas = []
binaries = []

for package in ("matplotlib", "scipy", "seaborn"):
    package_datas, package_binaries, package_imports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_imports

app = project_root + "/dstat_interface/main.py"

# Bundle theme assets (QSS + icons) so they resolve at runtime.
import os
_theme_dir = os.path.join(project_root, "dstat_interface", "core", "interface")
datas += [(os.path.join(_theme_dir, "styles.qss"), "dstat_interface/core/interface")]
datas += [(os.path.join(_theme_dir, "icons"), "dstat_interface/core/interface/icons")]

a = Analysis(
    [app],
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DStat-GUI-dev2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DStat-GUI-dev2",
)
