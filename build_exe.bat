@echo off
setlocal EnableDelayedExpansion
REM Builds a standalone Windows .exe for HYDRA-UMC SUITE.
REM Run this on a Windows machine with Python installed.
REM
REM Usage:
REM   build_exe.bat
REM
REM Output: dist\HYDRA-UMC_SUITE.exe (no Python installation needed to run it)

echo.
echo  ===============================================================
echo   H Y D R A - U M C   S U I T E  -  Windows build
echo  ===============================================================
echo   Multi-Controller Swarm Command Center
echo   Author:  JuanenRac (Electro Hobby 3D)
echo   E-mail:  electrohobby3d@gmail.com
echo   License: GPL-3.0 (see LICENSE) / BSD-3-Clause for assets\meshes\ur5e\
echo  ===============================================================
echo.

REM NOTE: every step below runs through "python -m" rather than calling
REM pip/pyinstaller directly - same reasoning as URTC-FLASHER's own
REM build_exe.bat (this project's sibling): pip.exe/pyinstaller.exe both
REM land in Python's Scripts\ folder, which isn't always on PATH (common
REM if Python was installed without checking "Add Python to PATH").
REM "python -m" finds the installed module directly instead of needing
REM its wrapper .exe to be on PATH.

echo [1/5] Creating/activating virtual environment...
REM A dedicated venv here (not "pip install --user" or a global install)
REM keeps this build reproducible against exactly requirements.txt's own
REM pinned versions, and matches how this project was actually developed
REM (see README.md's own "Getting Started" section) - PyInstaller freezes
REM whatever's importable in the active environment, so a venv with only
REM this project's real dependencies (not whatever else happens to be
REM globally installed) is what keeps dist\HYDRA-UMC_SUITE.exe's own
REM size and behavior predictable.
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
echo       Done.
echo.

echo [2/5] Installing Python dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
python -m pip install pyinstaller
echo       Done.
echo.

echo [3/5] Cleaning previous build...
REM Clean slate before compiling: build\ holds PyInstaller's intermediate
REM artifacts (its own bytecode/dependency cache), and dist\ holds the
REM previous output - removing both first means nothing stale from an
REM earlier build can survive into this one, rather than relying on
REM --noconfirm alone to just overwrite the final .exe.
if exist build rmdir /s /q build
if exist dist (
    rmdir /s /q dist
    if exist dist (
        echo       ERROR: couldn't remove dist\ - is HYDRA-UMC_SUITE.exe currently running?
        echo       Close it first, then run this script again.
        exit /b 1
    )
)
echo       Done.
echo.

echo [4/5] Compiling HYDRA-UMC_SUITE.exe with PyInstaller...
REM --add-data uses ";" as the source/destination separator on Windows -
REM Linux/Mac PyInstaller uses ":" instead (see build_exe.sh). Bundles
REM assets\ (the industrial_dark.qss theme + the real UR5e STL mesh set +
REM its own ATTRIBUTION.txt) directly into the .exe - hydra_suite/ui/
REM theme.py and hydra_suite/render/viewport.py both locate it via
REM Path(__file__).resolve().parent.parent.parent, which still resolves
REM correctly once frozen (PyInstaller preserves the hydra_suite/ package
REM tree's own relative layout inside the extracted bundle, and
REM --add-data's own "assets;assets" destination lands exactly where
REM that relative walk expects it) - no source change needed for this to
REM work frozen vs. running from source.
REM
REM --collect-all PySide6: without this, a frozen PySide6 app very
REM commonly fails at runtime with "could not find or load the Qt
REM platform plugin windows" - PyInstaller's own static import analysis
REM finds the Python modules fine, but PySide6's own platform/image-
REM format/OpenGL plugins are native Qt plugins loaded dynamically at
REM runtime, not importable Python modules its analyzer can trace.
REM Collecting all of PySide6 explicitly is the documented fix.
REM
REM --windowed: no console window behind the Qt UI (matches URTC-FLASHER's
REM own Windows build) - this app logs to stdout for diagnostics while
REM running from source; add --console instead if you need that visible
REM in a built .exe while troubleshooting.
REM
REM No --icon yet: this project only has images\HYDRA_UMC_SUITE_BANNER.jpg
REM today, no .ico - add "--icon assets\icon.ico" here once one exists.
python -m PyInstaller --onefile --windowed --noconfirm --name "HYDRA-UMC_SUITE" ^
    --add-data "assets;assets" ^
    --collect-all PySide6 ^
    --hidden-import qasync ^
    --hidden-import websockets ^
    --hidden-import OpenGL.platform.win32 ^
    main.py
if not exist dist\HYDRA-UMC_SUITE.exe (
    echo       ERROR: PyInstaller did not produce dist\HYDRA-UMC_SUITE.exe - see the output above.
    exit /b 1
)
echo       Done.
echo.

echo [5/5] Copying files that must sit next to the .exe, not inside it...
REM README.md, LICENSE, docs\ROADMAP.md: read as reference documentation,
REM not by the app itself at runtime, but worth shipping alongside the
REM .exe the same way URTC-FLASHER ships its own README/LICENSE - a
REM distributed .exe with zero accompanying documentation or license text
REM is a real gap, not a cosmetic one.
if exist README.md (
    copy /Y README.md dist\README.md >nul
    echo       Copied README.md into dist\
)
if exist LICENSE (
    copy /Y LICENSE dist\LICENSE >nul
    echo       Copied LICENSE into dist\
)
if exist docs (
    xcopy /E /I /Y docs dist\docs >nul
    echo       Copied docs\ into dist\docs\
)
echo       Done.
echo.

echo  ===============================================================
echo   dist\HYDRA-UMC_SUITE.exe is ready to run - no Python needed.
echo  ===============================================================
echo.
pause
