# -*- mode: python ; coding: utf-8 -*-

# The 3D models under assets/meshes are not in the repository tree; they come from one verified package
# (docs/MESH_PACKAGE.md). Stop here, with the way out, instead of building a program with no models.
import subprocess
import sys

if subprocess.call([sys.executable, '-m', 'hydra_suite.mesh_pack', 'ensure', '--source', 'auto']) != 0:
    raise SystemExit('The 3D models are missing and could not be fetched (see above). Run build_exe.bat / build_exe.sh, '
                     'or python -m hydra_suite.mesh_pack ensure, and see docs/MESH_PACKAGE.md for working offline.')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('C:/Users/juane/Documents/GitHub/HYDRA-UMC-SUITE/.venv/Lib/site-packages/PySide6/plugins/platforms', 'PySide6/plugins/platforms'), ('C:/Users/juane/Documents/GitHub/HYDRA-UMC-SUITE/.venv/Lib/site-packages/PySide6/plugins/styles', 'PySide6/plugins/styles'), ('C:/Users/juane/Documents/GitHub/HYDRA-UMC-SUITE/.venv/Lib/site-packages/PySide6/plugins/imageformats', 'PySide6/plugins/imageformats'), ('C:/Users/juane/Documents/GitHub/HYDRA-UMC-SUITE/.venv/Lib/site-packages/PySide6/plugins/iconengines', 'PySide6/plugins/iconengines')],
    hiddenimports=['qasync', 'websockets', 'zeroconf', 'zeroconf.asyncio', 'zeroconf._utils.ipaddress', 'ifaddr', 'PySide6.QtOpenGL', 'OpenGL.platform.win32', 'keyring', 'keyring.backends', 'keyring.backends.Windows', 'keyring.backends.macOS', 'keyring.backends.SecretService', 'keyring.backends.kwallet', 'keyring.backends.fail', 'keyring.backends.null'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='HYDRA-UMC_SUITE',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
