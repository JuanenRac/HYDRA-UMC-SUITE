@echo off
REM =============================================================================
REM HYDRA-UMC SUITE - installer/build_installer.bat
REM Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
REM GPL-3.0 - see ../LICENSE
REM
REM Builds the real .exe (via ..\build_exe.bat) then compiles
REM windows_installer.iss into a real Windows installer - requires Inno
REM Setup (iscc.exe on PATH): https://jrsoftware.org/isinfo.php (free).
REM
REM Output: installer\output\HYDRA-UMC_SUITE_Setup.exe
REM =============================================================================
setlocal

echo [1/2] Building HYDRA-UMC_SUITE.exe (..\build_exe.bat)...
pushd ..
call build_exe.bat
if errorlevel 1 (
    echo ERROR: build_exe.bat failed - see its own output above.
    popd
    exit /b 1
)
popd
python "%~dp0..\bump_manifest_version.py" --sync
if errorlevel 1 (
    echo ERROR: manifest synchronization failed after build_exe.bat.
    pause
    exit /b 1
)

where iscc.exe >nul 2>nul
if errorlevel 1 (
    echo ERROR: iscc.exe not found on PATH - install Inno Setup first:
    echo   https://jrsoftware.org/isinfo.php
    exit /b 1
)

echo [2/2] Compiling the installer (windows_installer.iss)...
iscc.exe windows_installer.iss
if errorlevel 1 (
    echo ERROR: iscc.exe failed - see its own output above.
    exit /b 1
)

echo.
echo Done: installer\output\HYDRA-UMC_SUITE_Setup.exe
