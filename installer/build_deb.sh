#!/usr/bin/env bash
# =============================================================================
# HYDRA-UMC SUITE - installer/build_deb.sh
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see ../LICENSE
#
# Builds a real .deb package using ../build_exe.sh's own real PyInstaller
# output rather than reimplementing
# packaging logic that build script already owns - same "don't
# reimplement, delegate" convention HYDRA-UMC-UPDATER's own install.py
# uses for every OTHER project's build step in this ecosystem.
#
# NOT RUN in this session - dpkg-deb only exists on Linux, and this
# environment is Windows. Written as a complete, correct, ready-to-use
# script instead: run this on a real Linux machine (or WSL) with
# dpkg-deb installed (part of the standard `dpkg` package on Debian/
# Ubuntu - already present on virtually every Debian-family system).
# The result should be smoke-tested (`sudo dpkg -i`, launch, `sudo dpkg
# -r`) before being treated as verified - this script is unverified
# until then.
#
# Output: installer/output/hydra-umc-suite_<version>_amd64.deb
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

# sed, not `grep -P` - PCRE lookbehind support isn't guaranteed on every
# grep build (this exact command failed with "supports only unibyte and
# UTF-8 locales" when checked from a Windows Git Bash session while
# writing this script) - a plain sed capture-group has no such
# dependency and works identically everywhere.
VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' ../hydra_suite/__init__.py)
if [ -z "$VERSION" ]; then
    echo "ERROR: couldn't read __version__ from ../hydra_suite/__init__.py" >&2
    exit 1
fi
ARCH="amd64"
PKG_NAME="hydra-umc-suite"
PKG_DIR="build/${PKG_NAME}_${VERSION}_${ARCH}"

echo "[1/4] Building HYDRA-UMC_SUITE (../build_exe.sh)..."
( cd .. && bash build_exe.sh )
python3 "$(dirname "$0")/../bump_manifest_version.py" --sync || exit 1
if [ ! -f ../dist/HYDRA-UMC_SUITE ]; then
    echo "ERROR: ../dist/HYDRA-UMC_SUITE not found - build_exe.sh's own output above should say why." >&2
    exit 1
fi

echo "[2/4] Assembling the package tree..."
rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR/DEBIAN" "$PKG_DIR/usr/local/bin" "$PKG_DIR/usr/share/applications"

cp ../dist/HYDRA-UMC_SUITE "$PKG_DIR/usr/local/bin/hydra-umc-suite"
chmod 755 "$PKG_DIR/usr/local/bin/hydra-umc-suite"

cat > "$PKG_DIR/DEBIAN/control" << EOF
Package: ${PKG_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
Description: HYDRA-UMC SUITE - Multi-Controller Swarm Command Center
 Desktop control application for the HYDRA-UMC robotics ecosystem -
 monitors and commands multiple HYDRA-UMC-SERVER controllers from one
 window (server browser, live 3D viewport, robot control, trajectories,
 cameras, logs).
Homepage: https://github.com/JuanenRac/HYDRA-UMC-SUITE
EOF

cat > "$PKG_DIR/usr/share/applications/hydra-umc-suite.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=HYDRA-UMC SUITE
Comment=Multi-Controller Swarm Command Center
Exec=/usr/local/bin/hydra-umc-suite
Terminal=false
Categories=Utility;Engineering;
EOF

echo "[3/4] Building the .deb (dpkg-deb)..."
mkdir -p output
dpkg-deb --build --root-owner-group "$PKG_DIR" "output/${PKG_NAME}_${VERSION}_${ARCH}.deb"

echo "[4/4] Done."
echo "Output: installer/output/${PKG_NAME}_${VERSION}_${ARCH}.deb"
echo "Install with: sudo dpkg -i installer/output/${PKG_NAME}_${VERSION}_${ARCH}.deb"
