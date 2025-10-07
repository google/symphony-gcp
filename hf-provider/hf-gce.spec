# hf_gce.spec
# -*- mode: python ; coding: utf-8 -*-

import re
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# ---- 1) Read version from pyproject.toml at build time (no tomllib dependency)
_pyproj_text = Path("pyproject.toml").read_text(encoding="utf-8")
m = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"\s*$', _pyproj_text)
VERSION = m.group(1) if m else "0.0.0-dev"

# ---- 2) Emit a tiny runtime hook that sets an env var for the app to read
build_dir = Path("build")
build_dir.mkdir(exist_ok=True)
RUNTIME_HOOK = build_dir / "_set_version_runtime_hook.py"
RUNTIME_HOOK.write_text(
    "import os\n"
    f"os.environ['HF_APP_VERSION'] = '{VERSION}'\n",
    encoding="utf-8",
)

# ---- 3) Paths, hidden imports, and data files
PATHEX = ["src"]

HIDDENIMPORTS = []
# your package
HIDDENIMPORTS += collect_submodules("gce_provider")
# common dynamic import offenders:
HIDDENIMPORTS += collect_submodules("google")
HIDDENIMPORTS += collect_submodules("kubernetes")

DATAS = []
# bundle package data from your code as needed
DATAS += collect_data_files(
    "gce_provider",
    includes=["**/*.yaml", "**/*.yml", "**/*.json", "**/*.txt"],
)

# If you prefer to read pyproject.toml at runtime instead of env injection,
# uncomment the next line to bundle it, and handle _MEIPASS in your code:
# DATAS += [("pyproject.toml", "pyproject.toml")]

# ---- 4) Analysis / Build
a = Analysis(
    ["src/gce_provider/__main__.py"],
    pathex=PATHEX,
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDENIMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(RUNTIME_HOOK)],  # << inject version into env for frozen app
    excludes=[],
    noarchive=False,
    optimize=0,  # easier debugging; set to 1 when stable
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="hf-gce",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,           # safer default; flip to True if you use UPX
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,        # CLI tool; keep console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# ---- 5) (Optional) Windows file version resource
# If you want the EXE "File Properties -> Details" to show VERSION,
# generate a version resource file and pass it via EXE(..., version=...).
# Example (uncomment and adjust if you need it):
#
# VERSION_FILE = build_dir / "hf_gce_version.txt"
# VERSION_FILE.write_text(
#     "[Version]\n"
#     f"FileVersion={VERSION}\n"
#     f"ProductVersion={VERSION}\n"
#     "FileDescription=hf-gce\n"
#     "CompanyName=\n"
#     "LegalCopyright=\n",
#     encoding="utf-8",
# )
# exe.version = str(VERSION_FILE)
