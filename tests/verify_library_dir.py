# =============================================================================
# HYDRA-UMC SUITE - tests/verify_library_dir.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies, without any window, the one folder of the 3D model library that STUDIO, this app and the STL editor can share
# (HYDRA_UMC_LIBRARY_DIR): unset or wrong it changes nothing, set it replaces assets/meshes everywhere the models are read, and a mesh
# package is never installed over it.
# =============================================================================
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")

from hydra_suite import library_dir
from hydra_suite import mesh_pack

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


default = Path("assets/meshes")
with tempfile.TemporaryDirectory() as tmp:
    shared = Path(tmp) / "common"
    shared.mkdir()
    env = {library_dir.LIBRARY_DIR_ENV: str(shared)}
    check("unset keeps the folder of the app", (library_dir.shared_dir({}), library_dir.mesh_root(default, {})), (None, default))
    check("blank keeps the folder of the app", library_dir.mesh_root(default, {library_dir.LIBRARY_DIR_ENV: "  "}), default)
    check("a value that is not a folder keeps the folder of the app", library_dir.mesh_root(default, {library_dir.LIBRARY_DIR_ENV: str(Path(tmp) / "none")}), default)
    check("a folder replaces assets/meshes", library_dir.mesh_root(default, env), shared)

    # a process that starts with the variable set reads every model folder from it, and the mesh package leaves it alone
    code = (
        "import sys; sys.path.insert(0, '.');"
        "from hydra_suite import mesh_pack, heated_beds, racks, vacuum_tables;"
        "from pathlib import Path;"
        "print(mesh_pack.MESH_DIR); print(heated_beds.CATALOG_DIR); print(racks.ASSET_DIR); print(vacuum_tables.CATALOG_DIR);"
        "print(mesh_pack.ensure(source='download', log=print, lang='pt'))"
    )
    run = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8", env={**os.environ, **env, "PYTHONIOENCODING": "utf-8"})
    lines = run.stdout.splitlines()
    check("the process ran", run.returncode, 0)
    check("every model folder is under the shared folder", [Path(line) for line in lines[:4]], [shared, shared / "heatedbeds" / "default", shared / "racks" / "default", shared / "vacuum-tables" / "default"])
    check("the package installs nothing over it and says so in the language", lines[4:], [mesh_pack.say("shared", "pt", path=str(shared)), "0"])
    check("the shared folder was not written", list(shared.iterdir()), [])

languages = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
check("the shared-library sentence exists in the eight languages", all("{path}" in mesh_pack.MESSAGES[code].get("shared", "") for code in languages), True)

print(f"FAILURES: {failures}")
sys.exit(1 if failures else 0)
