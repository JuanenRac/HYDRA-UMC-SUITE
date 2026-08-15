#!/usr/bin/env bash
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

echo
echo " ==============================================================="
echo "  H Y D R A - U M C   S U I T E  -  Linux build"
echo " ==============================================================="
echo "  Multi-Controller Swarm Command Center"
echo "  Author:  JuanenRac (Electro Hobby 3D)"
echo "  E-mail:  electrohobby3d@gmail.com"
echo "  License: GPL-3.0 (see LICENSE) / BSD-3-Clause for assets/meshes/ur5e/"
echo " ==============================================================="
echo

# PySide6 on Linux needs the real Qt platform (xcb by default) and OpenGL
# runtime libraries present on the SYSTEM, not just importable Python
# packages - pip installing PySide6 does not install libGL.so.1/libxcb*
# themselves. Checked explicitly here with a clear message instead of
# letting the build succeed and then fail confusingly with a "could not
# load the Qt platform plugin xcb" or a GL context error at runtime.
echo "[1/6] Checking for system Qt/OpenGL runtime libraries..."
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

echo "[3/6] Installing Python dependencies..."
python3 -m pip install --upgrade pip >/dev/null
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller
echo "      Done."
echo

echo "[4/6] Cleaning previous build..."
# Clean slate before compiling: build/ holds PyInstaller's intermediate
# artifacts (its own bytecode/dependency cache), and dist/ holds the
# previous output - removing both first means nothing stale from an
# earlier build can survive into this one, rather than relying on
# --noconfirm alone to just overwrite the final binary.
rm -rf build dist
echo "      Done."
echo

echo "[5/6] Compiling HYDRA-UMC_SUITE with PyInstaller..."
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

echo "[6/6] Copying files that must sit next to the binary, not inside it..."
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
echo "      Done."
echo

echo " ==============================================================="
echo "  Build complete: dist/HYDRA-UMC_SUITE is ready to run - no Python needed."
echo "  (chmod +x dist/HYDRA-UMC_SUITE if it isn't already executable)"
echo " ==============================================================="
echo
