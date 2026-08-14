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
# --collect-all PySide6: without this, a frozen PySide6 app very commonly
# fails at runtime with "could not find or load the Qt platform plugin" -
# PyInstaller's own static import analysis finds the Python modules fine,
# but PySide6's own platform/image-format/OpenGL plugins are native Qt
# plugins loaded dynamically at runtime, not importable Python modules
# its analyzer can trace. Collecting all of PySide6 explicitly is the
# documented fix.
#
# assets/ (theme QSS + real UR5e STL mesh set) bundled the same way as
# the Windows build - hydra_suite/ui/theme.py and
# hydra_suite/render/viewport.py both locate it via
# Path(__file__).resolve().parent.parent.parent, which still resolves
# correctly once frozen since PyInstaller preserves the hydra_suite/
# package's own relative layout inside the extracted bundle.
#
# No --windowed here, matching URTC-FLASHER's own build_exe.sh (that
# flag only means something on Windows/macOS bundlers - a Linux binary
# launched from a terminal doesn't have a separate "console window"
# concept to suppress the same way).
python3 -m PyInstaller --onefile --noconfirm --name "HYDRA-UMC_SUITE" \
    --add-data "assets:assets" \
    --collect-all PySide6 \
    --hidden-import qasync \
    --hidden-import websockets \
    main.py
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
