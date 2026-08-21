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
echo   HYDRA-UMC SUITE
echo  ===============================================================
echo   This script builds a standalone Windows .exe
echo   (dist\HYDRA-UMC_SUITE.exe) - Multi-Controller Swarm Command
echo   Center for the HYDRA-UMC platform. No Python installation is
echo   needed to run the result.
echo   Copyright (C) 2026 JuanenRac (Electro Hobby 3D) ^<electrohobby3d@gmail.com^>
echo   GPL-3.0 - see LICENSE (assets\meshes\ under their own per-robot
echo   licenses - see each folder's own ATTRIBUTION.txt)
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

echo [2/6] Installing Python dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
python -m pip install pyinstaller
echo       Done.
echo.

echo [3/6] Bumping version number...
REM Ecosystem-wide versioning policy: the version in hydra_suite/__init__.py
REM goes up on every REAL build (this script), not on every plain run of
REM main.py - base-10 "odometer" rule (patch+1; past 9 it resets to 0 and
REM carries into minor, e.g. 0.1.9 -> 0.2.0). See bump_version.py itself
REM for the full rule. Runs BEFORE PyInstaller so the compiled .exe always
REM carries the new, not-yet-shipped version number.
python bump_version.py
if errorlevel 1 (
    echo       ERROR: bump_version.py failed - see the output above.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [4/6] Cleaning previous build...
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
        pause
        exit /b 1
    )
)
echo       Done.
echo.

echo [5/6] Compiling HYDRA-UMC_SUITE.exe with PyInstaller...
REM --add-data uses ";" as the source/destination separator on Windows -
REM Linux/Mac PyInstaller uses ":" instead (see build_exe.sh). Bundles
REM assets\ (the industrial_dark.qss theme + the real STL mesh sets +
REM their own ATTRIBUTION.txt files) directly into the .exe - hydra_suite/ui/
REM theme.py and hydra_suite/render/viewport.py both locate it via
REM Path(__file__).resolve().parent.parent.parent, which still resolves
REM correctly once frozen (PyInstaller preserves the hydra_suite/ package
REM tree's own relative layout inside the extracted bundle, and
REM --add-data's own "assets;assets" destination lands exactly where
REM that relative walk expects it) - no source change needed for this to
REM work frozen vs. running from source.
REM
REM PySide6 packaging - NOT --collect-all: an earlier build used
REM --collect-all PySide6 (needed so the frozen .exe can find its own Qt
REM platform plugin at runtime - PyInstaller's own import analysis finds
REM the Python modules fine, but PySide6's platform/style/image-format
REM plugins are native Qt plugins loaded dynamically, not importable
REM Python modules it can trace), which produced a ~270MB .exe - it
REM copies the ENTIRE PySide6 package (Qt6WebEngineCore.dll ALONE is
REM ~196MB, plus qml/, translations/, opengl32sw.dll, none of which this
REM app imports - only QtCore/QtGui/QtWidgets/QtOpenGL/QtOpenGLWidgets
REM are actually used). --exclude-module does NOT fix this - it only
REM prunes PyInstaller's own Python IMPORT graph, not collect-all's own
REM raw data-file copy, which still runs regardless (confirmed by
REM testing: a build with --collect-all PySide6 plus a full list of
REM --exclude-module flags came out the SAME ~280MB size). The real fix:
REM drop collect-all entirely and manually stage only the 4 plugin
REM subfolders this app's own runtime hook actually needs
REM (platforms/styles/imageformats/iconengines, ~4.5MB total) via
REM --add-data, letting PyInstaller's normal binary-dependency scan find
REM the real Qt6Core/Gui/Widgets/OpenGL DLLs on its own (it can, since
REM those ARE real imported Python extension modules) - verified this
REM produces a working .exe (launches, GL viewport renders) at ~89MB,
REM roughly a two-thirds reduction.
if not defined PYSIDE_DIR (
    for /f "delims=" %%P in ('python -c "import PySide6, os; print(os.path.dirname(PySide6.__file__))"') do set PYSIDE_DIR=%%P
)
python -m PyInstaller --onefile --windowed --noconfirm --name "HYDRA-UMC_SUITE" ^
    --add-data "assets;assets" ^
    --add-data "%PYSIDE_DIR%\plugins\platforms;PySide6\plugins\platforms" ^
    --add-data "%PYSIDE_DIR%\plugins\styles;PySide6\plugins\styles" ^
    --add-data "%PYSIDE_DIR%\plugins\imageformats;PySide6\plugins\imageformats" ^
    --add-data "%PYSIDE_DIR%\plugins\iconengines;PySide6\plugins\iconengines" ^
    --hidden-import qasync ^
    --hidden-import websockets ^
    --hidden-import zeroconf ^
    --hidden-import zeroconf.asyncio ^
    --hidden-import zeroconf._utils.ipaddress ^
    --hidden-import ifaddr ^
    --hidden-import PySide6.QtOpenGL ^
    --hidden-import PySide6.QtOpenGLWidgets ^
    --hidden-import OpenGL.platform.win32 ^
    main.py
REM UPX (https://upx.github.io/) shrinks the final .exe further (30-50
REM percent typical) at zero functional cost - PyInstaller auto-detects and uses
REM it automatically if upx.exe is anywhere on PATH, no flag needed here.
REM Not bundled/installed by this script (a separate native tool, not a
REM pip package) - install it once and re-run this script to pick it up.
if not exist dist\HYDRA-UMC_SUITE.exe (
    echo       ERROR: PyInstaller did not produce dist\HYDRA-UMC_SUITE.exe - see the output above.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [6/6] Copying files that must sit next to the .exe, not inside it...
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
REM language\ sits NEXT TO the .exe (not bundled inside via --add-data)
REM deliberately - hydra_suite\i18n.py's own LANGUAGE_FOLDER resolves via
REM sys.executable's own directory for a frozen build (same reasoning as
REM URTC-FLASHER's own language\ folder), which also means a user or
REM translator can edit/add a .lng file after the fact without needing a
REM rebuild.
if exist language (
    xcopy /E /I /Y language dist\language >nul
    echo       Copied language\ into dist\language\
)
echo       Done.
echo.

echo  ===============================================================
echo   dist\HYDRA-UMC_SUITE.exe is ready to run - no Python needed.
echo  ===============================================================
echo.
pause
