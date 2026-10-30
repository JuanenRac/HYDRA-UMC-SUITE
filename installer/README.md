# Installers 📦

Goal: create a professional `.msi`/`.deb` installer.

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

## Language files

The window text lives in the `language` folder next to the program (`hydra_suite/i18n.py`). Both installers copy that folder (`windows_installer.iss` into `{app}\language`, `build_deb.sh` into `/usr/share/hydra-umc-suite/language`); a package built without it would show every label as its key. Check that the folder is present after installing.

## Verification status

Neither script was run end-to-end in the session that wrote them - Inno Setup wasn't installed (and installing new system-wide tooling wasn't done without asking first), and `dpkg-deb` only exists on Linux, unavailable from that Windows dev machine. What *was* verified there: `build_deb.sh` passes `bash -n` (syntax check), and its version-extraction + package-tree-assembly logic was dry-run in isolation with a placeholder binary, producing the exact expected file tree and a correct `DEBIAN/control`. Treat both scripts as **written and reasoned through, not yet proven** until someone with the right tooling actually runs one end to end and smoke-tests the result (install, launch, uninstall).

## Authenticode and how to verify the installer

The Windows installer is not signed with Authenticode (that needs a paid code-signing certificate), so Windows SmartScreen may warn when it is run. Each release publishes, next to the installer, a SHA-256 checksum (`.sha256`) and an Ed25519 signature (`.sig`) of it, made with the HYDRA release key. Before running the installer, compare the checksum (`sha256sum`, or `Get-FileHash -Algorithm SHA256` on Windows) and verify the signature with `hydra-sign verify --pub PUBLIC.pem FILE` from HYDRA-UMC-TOOL-CLI, using the public key of the release key. This only proves the file is the one that was published; it does not replace Authenticode.
