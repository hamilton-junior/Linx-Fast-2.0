"""Build script to generate version and produce a PyInstaller onefile bundle.

This script replaces the previous `build.bat` and follows a simple, testable
Python approach. It is platform-aware for Windows paths used by the project.
"""

from __future__ import annotations

import subprocess
import sys
import re
from pathlib import Path

# generate version.py using the project's script
try:
    import generate_version

    try:
        generate_version.write_version_py()
    except Exception:
        # fallback to executing as a script
        subprocess.run([sys.executable, "generate_version.py"], check=False)
except Exception:
    # if the helper can't be imported, try running it directly
    try:
        subprocess.run([sys.executable, "generate_version.py"], check=False)
    except Exception:
        pass

# Parse version info from version.py
VERSION = "0.0.0"
BUILD_DATE = ""
here = Path(__file__).resolve().parent
version_file = here / "version.py"
if version_file.exists():
    text = version_file.read_text(encoding="utf-8")
    m_v = re.search(r"VERSION\s*=\s*['\"]([^'\"]+)['\"]", text)
    m_d = re.search(r"BUILD_DATE\s*=\s*['\"]([^'\"]+)['\"]", text)
    if m_v:
        VERSION = m_v.group(1)
    if m_d:
        BUILD_DATE = m_d.group(1).split()[0]

# Prepare output directories (original behavior used the user's Desktop)
desktop = Path(r"C:\OneDrive\OneDrive - Linx SA\Área de Trabalho")
DIST_FOLDER = desktop / f"LinxFast2.0 - {VERSION} - {BUILD_DATE}"
WORK_FOLDER = desktop / "build"
DIST_FOLDER.mkdir(parents=True, exist_ok=True)
WORK_FOLDER.mkdir(parents=True, exist_ok=True)

# Build with PyInstaller (if available)
pyinstaller_cmd = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--onefile",
    "--noconsole",
    "--icon=LinxFast2.ico",
    "--add-data",
    "templates;templates",
    "--add-data",
    "assets/images;assets/images",
    "--distpath",
    str(DIST_FOLDER),
    "--workpath",
    str(WORK_FOLDER),
    "--name",
    "LinxFast2",
    "app.py",''
]

print("Running PyInstaller... this may take a while")
try:
    subprocess.run(pyinstaller_cmd, check=True)
    print("Build finished. Output folder:", DIST_FOLDER)
except subprocess.CalledProcessError as e:
    print("Build failed:", e)
    sys.exit(1)
