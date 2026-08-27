# Installers 📦

Audit idea: "Crear un instalador `.msi`/`.deb` profesional" (`SONNET/AUDITORIA_COMPLETA_44_PROYECTOS.txt`).

Both scripts here delegate the actual build to this project's own `../build_exe.bat`/`.sh` (the real PyInstaller step already lives there - see `HYDRA-UMC-UPDATER/install.py`'s own header comment for why this ecosystem never reimplements a project's own build logic in a second place) and only add packaging on top of that real output.

## Windows: `windows_installer.iss` + `build_installer.bat`

A real Windows installer via [Inno Setup](https://jrsoftware.org/isinfo.php) (free) - not literally an `.msi` (that would need the heavier WiX Toolset), but the standard, Windows-native equivalent: Start Menu entry, optional desktop icon, a real uninstaller, installed per-user (no admin elevation needed).

```
installer\build_installer.bat
```

Needs Inno Setup's `iscc.exe` on `PATH`. Output: `installer\output\HYDRA-UMC_SUITE_Setup.exe`.

## Linux: `build_deb.sh`

A real `.deb` package - installs the binary to `/usr/local/bin/hydra-umc-suite` and adds a desktop launcher entry (`/usr/share/applications/`).

```bash
./installer/build_deb.sh
sudo dpkg -i installer/output/hydra-umc-suite_<version>_amd64.deb
```

Needs `dpkg-deb` (part of the standard `dpkg` package - already present on virtually every Debian-family system). Run on a real Linux machine (or WSL) - `dpkg-deb` doesn't exist on Windows.

## Verification status

Neither script was run end-to-end in the session that wrote them - Inno Setup wasn't installed (and installing new system-wide tooling wasn't done without asking first), and `dpkg-deb` only exists on Linux, unavailable from that Windows dev machine. What *was* verified there: `build_deb.sh` passes `bash -n` (syntax check), and its version-extraction + package-tree-assembly logic was dry-run in isolation with a placeholder binary, producing the exact expected file tree and a correct `DEBIAN/control`. Treat both scripts as **written and reasoned through, not yet proven** until someone with the right tooling actually runs one end to end and smoke-tests the result (install, launch, uninstall).
