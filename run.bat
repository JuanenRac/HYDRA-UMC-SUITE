@echo off
rem Keep the window open for people, never in automation (CI / HYDRA_UMC_CI).
set "KEEP_OPEN=pause"
if defined CI set "KEEP_OPEN=ver >nul"
if "%HYDRA_UMC_CI%"=="1" set "KEEP_OPEN=ver >nul"
REM HYDRA_UMC_SCRIPT_STANDARD_HEADER_BEGIN
REM *****************************************************************************
REM Project   : HYDRA-UMC-SUITE
REM Script    : run.bat
REM Purpose   : Runtime workflow for the project entry point.
REM Author    : JuanenRac (Electro Hobby 3D)
REM Email     : electrohobby3d@gmail.com
REM Copyright : (C) 2026 JuanenRac
REM License   : GPL-3.0 - see LICENSE
REM *****************************************************************************
REM HYDRA_UMC_SCRIPT_STANDARD_HEADER_END
REM HYDRA_UMC_SCRIPT_STANDARD_BANNER_BEGIN
echo.
echo *****************************************************************************
echo * HYDRA-UMC-SUITE - run.bat
echo * Mode      : RUN WORKFLOW
echo * Author    : JuanenRac (Electro Hobby 3D)
echo * Email     : electrohobby3d@gmail.com
echo * Copyright : (C) 2026 JuanenRac
echo * License   : GPL-3.0 - see LICENSE
echo * ------------------------------------------------------------------------- *
echo * 1. Resolve the runtime prerequisites declared by this script.
echo * 2. Start the project entry point and forward user arguments unchanged.
echo * 3. Preserve its result and keep an interactive terminal open.
echo *****************************************************************************
echo.
REM HYDRA_UMC_SCRIPT_STANDARD_BANNER_END
REM Runs HYDRA-UMC-SUITE from source. build_exe.bat produces a standalone
REM .exe instead; this script is the quick "run it right now" path.
cd /d "%~dp0"

REM The python of the venv is used directly (no activate script); without a venv the python on the PATH is used.
set "VPY=python"
if exist .venv\Scripts\python.exe set "VPY=%CD%\.venv\Scripts\python.exe"

REM Fetches the verified mesh package only when mesh_pack.config.json (or HYDRA_UMC_MESH_SOURCE) asks for it;
REM with the default source (local) this does nothing.
"%VPY%" -m hydra_suite.mesh_pack prepare
if errorlevel 1 goto :done
"%VPY%" main.py %*
:done
%KEEP_OPEN%
