# =============================================================================
# HYDRA-UMC SUITE - tests/verify_build_scripts.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Reads (never runs) the build scripts, which raise the version when run:
#   - the executable carries the window icon files (images/) and, on Windows,
#     its own icon
#   - the steps are numbered in order, once each, with the same total
#   - build_exe.bat does not wait for a key when the installer script calls it
#   - the Windows script has no unreachable second check of the version bump
# =============================================================================
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


sh = (ROOT / "build_exe.sh").read_text(encoding="utf-8")
bat = (ROOT / "build_exe.bat").read_text(encoding="utf-8")
installer = (ROOT / "installer" / "build_installer.bat").read_text(encoding="utf-8")

check("sh: images are packaged", '--add-data "images:images"' in sh, True)
check("bat: images are packaged", '--add-data "images;images"' in bat, True)
check("bat: the executable has its icon", "--icon" in bat and "HYDRA_UMC_ICON.ico" in bat, True)
check("images exist", (ROOT / "images" / "HYDRA_UMC_ICON.ico").is_file() and (ROOT / "images" / "HYDRA_UMC_ICON.svg").is_file(), True)

for name, text in (("sh", sh), ("bat", bat)):
    steps = re.findall(r'(?m)^\s*(?:echo|printf \'%s\\n\')\s+"?\[(\d+)/(\d+)\]', text)
    numbers = [int(a) for a, _ in steps]
    totals = {int(b) for _, b in steps}
    check(f"{name}: steps are in order", numbers, list(range(1, len(numbers) + 1)))
    check(f"{name}: one total", len(totals), 1)
    check(f"{name}: the total is the number of steps", totals == {len(numbers)}, True)

check("bat: the pause can be switched off by the installer", 'HYDRA_UMC_NO_PAUSE' in bat, True)
check("installer: asks the build not to pause", 'set "HYDRA_UMC_NO_PAUSE=1"' in installer, True)
check("bat: the version bump is checked once", bat.count("bump_version.py failed"), 0)

print("FAILURES:", failures)
sys.exit(1 if failures else 0)
