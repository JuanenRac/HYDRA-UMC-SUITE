@echo off
REM HYDRA_UMC_SCRIPT_STANDARD_HEADER_BEGIN
REM *****************************************************************************
REM Project   : HYDRA-UMC-SUITE
REM Script    : build_exe.bat
REM Purpose   : Incremental standalone executable build and packaging workflow.
REM Author    : JuanenRac (Electro Hobby 3D)
REM Email     : electrohobby3d@gmail.com
REM Copyright : (C) 2026 JuanenRac
REM License   : GPL-3.0 - see LICENSE
REM *****************************************************************************
REM HYDRA_UMC_SCRIPT_STANDARD_HEADER_END
REM HYDRA_UMC_SCRIPT_STANDARD_BANNER_BEGIN
echo.
echo *****************************************************************************
echo * HYDRA-UMC-SUITE - build_exe.bat
echo * Mode      : INCREMENTAL BUILD
echo * Author    : JuanenRac (Electro Hobby 3D)
echo * Email     : electrohobby3d@gmail.com
echo * Copyright : (C) 2026 JuanenRac
echo * License   : GPL-3.0 - see LICENSE
echo * ------------------------------------------------------------------------- *
echo * 1. Read the project version (building never changes it; use the explicit bump command).
echo * 2. Run this project's declared build, verification and packaging commands.
echo * 3. Report the result and keep an interactive terminal open.
echo *****************************************************************************
echo.
REM HYDRA_UMC_SCRIPT_STANDARD_BANNER_END
setlocal EnableDelayedExpansion
rem Keep the window open for people, never in automation (CI / HYDRA_UMC_CI).
set "KEEP_OPEN=pause"
if defined CI set "KEEP_OPEN=ver >nul"
if "%HYDRA_UMC_CI%"=="1" set "KEEP_OPEN=ver >nul"
rem build_installer.bat sets this so the build does not wait for a key press.
if "%HYDRA_UMC_NO_PAUSE%"=="1" set "KEEP_OPEN=ver >nul"
echo [1/6] Creating/activating virtual environment...
REM The venv is made with the py launcher when there is one (the python that is first on the PATH may be a stripped one, for example the one of ESP-IDF, whose
REM venv has no activate script), and the scripts use the python of the venv directly instead of activating it.
set "PYMAKE=python"
where py >nul 2>nul && set "PYMAKE=py -3"
if not exist .venv\Scripts\python.exe (
    %PYMAKE% -m venv .venv
    if errorlevel 1 goto :error
)
if not exist .venv\Scripts\python.exe (
    echo ERROR: .venv has no python.exe; delete the .venv folder and run this again.
    goto :error
)
set "VPY=%CD%\.venv\Scripts\python.exe"
echo       Done.
echo.

echo [2/6] Installing Python dependencies...
"%VPY%" -m pip install --upgrade pip >nul
"%VPY%" -m pip install -r requirements.txt
"%VPY%" -m pip install pyinstaller
echo       Done.
echo.

REM HYDRA_UMC_SCRIPT_STANDARD_VERSION_STEP
echo [3/6] Reading the project version (building never changes it)...
for /f "usebackq delims=" %%V in (`python -c "import json; print(json.load(open(r'%~dp0hydra-umc.project.json', encoding='utf-8'))['version'])"`) do set "HYDRA_UMC_VERSION_BUILT=%%V"
if not defined HYDRA_UMC_VERSION_BUILT set "HYDRA_UMC_VERSION_BUILT=unknown"
echo       Building v%HYDRA_UMC_VERSION_BUILT% (building never changes the version)
echo.
echo.
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
        %KEEP_OPEN%
        exit /b 1
    )
)
echo       Done.
echo.

echo [5/6] Compiling HYDRA-UMC_SUITE.exe with PyInstaller...
REM The 3D models are not in the repository tree: they come from one verified package (see docs\MESH_PACKAGE.md).
REM They are fetched here, before PyInstaller packs assets\, so the .exe is never built without them. Offline:
REM put the package in %USERPROFILE%\.cache\hydra-umc\meshes or set HYDRA_UMC_MESH_PACKAGE to its path.
echo       Checking the 3D models (verified package, cached)...
"%VPY%" -m hydra_suite.mesh_pack ensure --source auto
if errorlevel 1 (
    echo       ERROR: the 3D models are missing and could not be fetched - see the message above.
    %KEEP_OPEN%
    exit /b 1
)

REM --add-data uses ";" as the source/destination separator on Windows -
REM Linux/Mac PyInstaller uses ":" instead (see build_exe.sh). Bundles
REM assets\ (the QML interface + the real STL mesh sets +
REM their own ATTRIBUTION.txt files) directly into the .exe - qt_suite.py
REM and hydra_suite/render/viewport.py both locate it relative to their own
REM file, which still resolves
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
REM app imports - only QtCore/QtGui/QtOpenGL/QtSvg/QtQml/QtQuick/QtQuickControls2
REM are actually used). --exclude-module does NOT fix this - it only
REM prunes PyInstaller's own Python IMPORT graph, not collect-all's own
REM raw data-file copy, which still runs regardless (confirmed by
REM testing: a build with --collect-all PySide6 plus a full list of
REM --exclude-module flags came out the SAME ~280MB size). The real fix:
REM drop collect-all entirely and manually stage only the 4 plugin
REM subfolders this app's own runtime hook actually needs
REM (platforms/styles/imageformats/iconengines, ~4.5MB total) via
REM --add-data, letting PyInstaller's normal binary-dependency scan find
REM the real Qt6 Core/Gui/Widgets/OpenGL and the other Qt DLLs on its own (it can, since
REM those ARE real imported Python extension modules) - verified this
REM produces a working .exe (launches, GL viewport renders) at ~89MB,
REM roughly a two-thirds reduction.
if not defined PYSIDE_DIR (
    for /f "delims=" %%P in ('""%VPY%" -c "import PySide6, os; print(os.path.dirname(PySide6.__file__))""') do set PYSIDE_DIR=%%P
)
"%VPY%" -m PyInstaller --onefile --windowed --noconfirm --name "HYDRA-UMC_SUITE" ^
    --add-data "assets;assets" ^
    --add-data "images;images" ^
    --icon "images\HYDRA_UMC_ICON.ico" ^
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
    --hidden-import keyring ^
    --hidden-import keyring.backends ^
    --hidden-import keyring.backends.Windows ^
    --hidden-import keyring.backends.macOS ^
    --hidden-import keyring.backends.SecretService ^
    --hidden-import keyring.backends.kwallet ^
    --hidden-import keyring.backends.fail ^
    --hidden-import keyring.backends.null ^
    --hidden-import PySide6.QtOpenGL ^
    --hidden-import PySide6.QtQml ^
    --hidden-import PySide6.QtQuick ^
    --hidden-import OpenGL.platform.win32 ^
    main.py
REM UPX (https://upx.github.io/) shrinks the final .exe further (30-50
REM percent typical) at zero functional cost - PyInstaller auto-detects and uses
REM it automatically if upx.exe is anywhere on PATH, no flag needed here.
REM Not bundled/installed by this script (a separate native tool, not a
REM pip package) - install it once and re-run this script to pick it up.
if not exist dist\HYDRA-UMC_SUITE.exe (
    echo       ERROR: PyInstaller did not produce dist\HYDRA-UMC_SUITE.exe - see the output above.
    %KEEP_OPEN%
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
if exist CHANGELOG.md (
    REM A07: README.md's own CHANGELOG.md link is correct in the
    REM canonical repo, but dist/ never carried CHANGELOG.md alongside
    REM its own copied README.md - a dangling link in the distributed
    REM copy only.
    copy /Y CHANGELOG.md dist\CHANGELOG.md >nul
    echo       Copied CHANGELOG.md into dist\
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
echo Built v%HYDRA_UMC_VERSION_BUILT%. Building never changes the version; to raise it run: python tools\hydra_project_tool.py bump
echo.
%KEEP_OPEN%
