#!/usr/bin/env bash
# HYDRA_UMC_SCRIPT_STANDARD_HEADER_BEGIN
# *****************************************************************************
# Project   : HYDRA-UMC-SUITE
# Script    : build_exe.sh
# Purpose   : Incremental standalone executable build and packaging workflow.
# Author    : JuanenRac (Electro Hobby 3D)
# Email     : electrohobby3d@gmail.com
# Copyright : (C) 2026 JuanenRac
# License   : GPL-3.0 - see LICENSE
# *****************************************************************************
# HYDRA_UMC_SCRIPT_STANDARD_HEADER_END
# HYDRA_UMC_SCRIPT_STANDARD_BANNER_BEGIN
printf '\n*******************************************************************************\n'
printf '%s\n' "* HYDRA-UMC-SUITE - build_exe.sh"
printf '%s\n' "* Mode      : INCREMENTAL BUILD"
printf '%s\n' "* Author    : JuanenRac (Electro Hobby 3D)"
printf '%s\n' "* Email     : electrohobby3d@gmail.com"
printf '%s\n' "* Copyright : (C) 2026 JuanenRac"
printf '%s\n' "* License   : GPL-3.0 - see LICENSE"
printf '%s\n' "* ------------------------------------------------------------------------- *"
printf '%s\n' "* 1. Increment the project version and synchronise its manifest."
printf '%s\n' "* 2. Run this project's declared build, verification and packaging commands."
printf '%s\n' "* 3. Report the result and keep an interactive terminal open."
printf '%s\n' "*******************************************************************************"
printf '\n'
# HYDRA_UMC_SCRIPT_STANDARD_BANNER_END
# Builds a standalone Linux binary for HYDRA-UMC SUITE.
# Run this on the Linux machine you actually want to run it on - unlike
# cross-compiling, PyInstaller builds a binary for whatever OS it runs on,
# so this won't produce something usable on Windows, and build_exe.bat
# won't produce something usable here.
#
# Usage:
#   chmod +x build_exe.sh   (one-time)
#   ./build_exe.sh
#
# Output: dist/HYDRA-UMC_SUITE (no Python installation needed to run it)
#
# NOTE: python3 -m pip / python3 -m PyInstaller, same reasoning as
# build_exe.bat's Windows PATH note - calling the installed modules
# directly sidesteps any question of whether their wrapper scripts landed
# somewhere on PATH.
set -euo pipefail

# The window/terminal this script runs in must NOT close on its own once
# the script ends - the user needs to be able to read the full result,
# including any error message, before it goes away. An EXIT trap (rather
# than only a "read" at the very bottom of the file) is what makes this
# fire on EVERY way the script can end: a normal successful run falling
# off the end, an explicit `exit 1` below, AND a command failing under
# `set -e` above (e.g. a pip/PyInstaller failure that isn't behind one of
# this script's own explicit checks) - bash always runs the EXIT trap
# right before the shell actually exits, regardless of which of those 3
# triggered it.
trap 'echo; read -r -p "Press Enter to close..." _ || true' EXIT
if ! python3 -c "import ctypes; ctypes.CDLL('libGL.so.1')" 2>/dev/null; then
    echo "      libGL.so.1 not found."
    echo "      On Debian/Ubuntu:  sudo apt install libgl1 libxkbcommon-x11-0 libxcb-cursor0"
    echo "      On Fedora:         sudo dnf install mesa-libGL libxkbcommon-x11 xcb-util-cursor"
    echo "      On Arch:           sudo pacman -S libglvnd libxkbcommon-x11 xcb-util-cursor"
    exit 1
fi
echo "      Found."
echo

echo "[2/6] Creating/activating virtual environment..."
# Same reasoning as build_exe.bat's own step 1 - a dedicated venv keeps
# this build reproducible against exactly requirements.txt's own pinned
# versions, not whatever else happens to be globally installed.
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
echo "      Done."
echo

echo "[3/7] Installing Python dependencies..."
python3 -m pip install --upgrade pip >/dev/null
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller
echo "      Done."
echo

echo "[4/7] Bumping version number..."
# Ecosystem-wide versioning policy: the version in hydra_suite/__init__.py
# goes up on every REAL build (this script), not on every plain run of
# main.py - base-10 "odometer" rule (patch+1; past 9 it resets to 0 and
# carries into minor, e.g. 0.1.9 -> 0.2.0). See bump_version.py itself for
# the full rule. Runs BEFORE PyInstaller so the compiled binary always
# carries the new, not-yet-shipped version number. `set -euo pipefail`
# above already aborts this script if bump_version.py exits non-zero.
# HYDRA_UMC_SCRIPT_STANDARD_VERSION_STEP
printf '%s\n' "[1/6] Incrementing project version and synchronising its manifest..."
python3 bump_version.py || exit 1
# HYDRA_UMC_SCRIPT_STANDARD_VERSION_CAPTURE_BEFORE
HYDRA_UMC_VERSION_BEFORE="$(python3 -c 'import json, pathlib, sys; print(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["version"])' "$(dirname "$0")/hydra-umc.project.json")"
python3 "$(dirname "$0")/bump_manifest_version.py" --sync || exit 1
# HYDRA_UMC_SCRIPT_STANDARD_VERSION_CAPTURE_AFTER
HYDRA_UMC_VERSION_AFTER="$(python3 -c 'import json, pathlib, sys; print(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["version"])' "$(dirname "$0")/hydra-umc.project.json")"
printf '\n*******************************************************************************\n'
printf '%s\n' '* VERSION INCREMENT COMPLETED'
printf '%s\n' "* v${HYDRA_UMC_VERSION_BEFORE:-unknown} -> v${HYDRA_UMC_VERSION_AFTER:-unknown}"
printf '%s\n' '* Project manifest has been synchronised by the project build flow.'
printf '%s\n' '*******************************************************************************'
printf '\n'
echo "      Done."
echo

echo "[5/7] Cleaning previous build..."
# Clean slate before compiling: build/ holds PyInstaller's intermediate
# artifacts (its own bytecode/dependency cache), and dist/ holds the
# previous output - removing both first means nothing stale from an
# earlier build can survive into this one, rather than relying on
# --noconfirm alone to just overwrite the final binary.
rm -rf build dist
echo "      Done."
echo

echo "[6/7] Compiling HYDRA-UMC_SUITE with PyInstaller..."
# assets/ (theme QSS + real STL mesh sets) bundled the same way as the
# Windows build - hydra_suite/ui/theme.py and
# hydra_suite/render/viewport.py both locate it via
# Path(__file__).resolve().parent.parent.parent, which still resolves
# correctly once frozen since PyInstaller preserves the hydra_suite/
# package's own relative layout inside the extracted bundle.
#
# No --windowed here, matching URTC-FLASHER's own build_exe.sh (that
# flag only means something on Windows/macOS bundlers - a Linux binary
# launched from a terminal doesn't have a separate "console window"
# concept to suppress the same way).
#
# PySide6 packaging - NOT --collect-all: an earlier version of this
# script used --collect-all PySide6 (needed so the frozen binary can
# find its own Qt platform plugin at runtime), which produced a ~270MB
# binary - it copies the ENTIRE PySide6 package (Qt6WebEngineCore alone
# is ~196MB, plus qml/, translations/, none of which this app imports -
# only QtCore/QtGui/QtWidgets/QtOpenGL/QtOpenGLWidgets are actually
# used). A follow-up attempt added --exclude-module for every unused Qt
# submodule on TOP of --collect-all, which does NOT fix this -
# --exclude-module only prunes PyInstaller's own Python IMPORT graph,
# not collect-all's own raw data-file copy, which still runs regardless
# (confirmed on the Windows build: --collect-all plus a full
# --exclude-module list came out the SAME ~280MB size). The real fix:
# drop collect-all entirely and manually stage only the plugin
# subfolders this app's own runtime hook actually needs
# (platforms/styles/imageformats/iconengines under Qt/plugins/ on Linux
# - note the extra "Qt/" level PySide6's own Linux layout has, unlike
# Windows' flat PySide6/plugins/) via --add-data, letting PyInstaller's
# normal binary-dependency scan find the real Qt6Core/Gui/Widgets/OpenGL
# .so files on its own (it can, since those ARE real imported Python
# extension modules) - verified on Windows this produces a working,
# ~89MB binary (roughly a two-thirds reduction); the same approach here.
PYSIDE_DIR=$(python3 -c "import PySide6, os; print(os.path.dirname(PySide6.__file__))")
python3 -m PyInstaller --onefile --noconfirm --name "HYDRA-UMC_SUITE" \
    --add-data "assets:assets" \
    --add-data "$PYSIDE_DIR/Qt/plugins/platforms:PySide6/Qt/plugins/platforms" \
    --add-data "$PYSIDE_DIR/Qt/plugins/styles:PySide6/Qt/plugins/styles" \
    --add-data "$PYSIDE_DIR/Qt/plugins/imageformats:PySide6/Qt/plugins/imageformats" \
    --add-data "$PYSIDE_DIR/Qt/plugins/iconengines:PySide6/Qt/plugins/iconengines" \
    --hidden-import qasync \
    --hidden-import websockets \
    --hidden-import zeroconf \
    --hidden-import zeroconf.asyncio \
    --hidden-import zeroconf._utils.ipaddress \
    --hidden-import ifaddr \
    --hidden-import PySide6.QtOpenGL \
    --hidden-import PySide6.QtOpenGLWidgets \
    main.py
# UPX (https://upx.github.io/) shrinks the final binary further (30-50
# percent typical) at zero functional cost - PyInstaller auto-detects
# and uses it automatically if the upx binary is anywhere on PATH, no
# flag needed here. Not installed by this script (a separate native
# tool, not a pip package) - install it (e.g. `sudo apt install
# upx-ucl`) and re-run this script to pick it up.
if [ ! -f dist/HYDRA-UMC_SUITE ]; then
    echo "      ERROR: PyInstaller did not produce dist/HYDRA-UMC_SUITE - see the output above."
    exit 1
fi
echo "      Done."
echo

echo "[7/7] Copying files that must sit next to the binary, not inside it..."
# README.md, LICENSE, docs/ROADMAP.md: reference documentation, not read
# by the app itself at runtime, but worth shipping alongside the binary
# the same way URTC-FLASHER ships its own README/LICENSE - a distributed
# binary with zero accompanying documentation or license text is a real
# gap, not a cosmetic one.
if [ -f README.md ]; then
    cp README.md dist/README.md
    echo "      Copied README.md into dist/"
fi
if [ -f LICENSE ]; then
    cp LICENSE dist/LICENSE
    echo "      Copied LICENSE into dist/"
fi
if [ -d docs ]; then
    mkdir -p dist/docs
    cp -r docs/. dist/docs/
    echo "      Copied docs/ into dist/docs/"
fi
# language/ sits NEXT TO the binary (not bundled inside via --add-data)
# deliberately - hydra_suite/i18n.py's own LANGUAGE_FOLDER resolves via
# sys.executable's own directory for a frozen build (same reasoning as
# URTC-FLASHER's own language/ folder), which also means a user or
# translator can edit/add a .lng file after the fact without a rebuild.
if [ -d language ]; then
    mkdir -p dist/language
    cp -r language/. dist/language/
    echo "      Copied language/ into dist/language/"
fi
echo "      Done."
echo

echo " ==============================================================="
echo "  Build complete: dist/HYDRA-UMC_SUITE is ready to run - no Python needed."
echo "  (chmod +x dist/HYDRA-UMC_SUITE if it isn't already executable)"
echo " ==============================================================="
echo
