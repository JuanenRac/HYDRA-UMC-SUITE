# =============================================================================
# HYDRA-UMC SUITE - tests/verify_readme_facts.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The numbers the READMEs state must be the real ones, in the eight languages:
#   - how many offline verify scripts there are under tests/
#   - how many dock panels the window has and how many of them the Qt Quick
#     shell has ported
# so a new test or panel cannot leave the documentation behind. No Qt needed.
# =============================================================================
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


sys.path.insert(0, str(ROOT / "tools"))
from run_offline_verifiers import discover_verifiers

VERIFIERS = len(discover_verifiers())

from hydra_suite.ui.nav_sidebar import ALL_DOCK_KEYS

suite = (ROOT / "qt_suite.py").read_text(encoding="utf-8")
DOCKS = len(set(ALL_DOCK_KEYS))
migrated_block = re.search(r"MIGRATED_PANELS = frozenset\(\{(.*?)\}\)", suite, re.S).group(1)
MIGRATED = len(set(re.findall(r'"(\w+)"', migrated_block)))

COUNT = {
    "README.md": r"(\d+) offline verify/smoke scripts",
    "README_deu.md": r"(\d+) Offline-Verify-/Smoke-Skripte",
    "README_fra.md": r"(\d+) scripts de vérification/smoke",
    "README_ita.md": r"(\d+) script di verifica/smoke",
    "README_jpn.md": r"(\d+)件のオフライン検証",
    "README_por.md": r"(\d+) scripts offline de verificação",
    "README_spa.md": r"(\d+) scripts de verificación/smoke",
    "README_zho.md": r"(\d+) 个离线校验",
}
PANELS = {
    "README.md": r"(\d+) of the (\d+) classic panels ported",
    "README_deu.md": r"(\d+) der (\d+) klassischen Panels portiert",
    "README_fra.md": r"(\d+) des (\d+) panneaux classiques portés",
    "README_ita.md": r"(\d+) dei (\d+) pannelli classici portati",
    "README_jpn.md": r"(\d+)の従来パネルのうち(\d+)が移植済み",
    "README_por.md": r"com (\d+) dos (\d+) painéis clássicos portados",
    "README_spa.md": r"(\d+) de los (\d+) paneles clásicos portados",
    "README_zho.md": r"(\d+) 个经典面板中的 (\d+) 个已移植",
}

check("there are verify scripts", VERIFIERS > 0, True)
check("the window has dock panels", DOCKS > 0 and MIGRATED <= DOCKS, True)
for name, pattern in COUNT.items():
    text = (ROOT / name).read_text(encoding="utf-8")
    match = re.search(pattern, text)
    check(f"{name}: verify script count", int(match.group(1)) if match else None, VERIFIERS)
for name, pattern in PANELS.items():
    text = (ROOT / name).read_text(encoding="utf-8")
    match = re.search(pattern, text)
    if name == "README_jpn.md":
        got = (int(match.group(1)), int(match.group(2))) if match else None
        check(f"{name}: ported panels", got, (DOCKS, MIGRATED))
    elif name == "README_zho.md":
        got = (int(match.group(1)), int(match.group(2))) if match else None
        check(f"{name}: ported panels", got, (DOCKS, MIGRATED))
    elif name in ("README_deu.md", "README_fra.md", "README_ita.md", "README_por.md", "README_spa.md", "README.md"):
        got = (int(match.group(1)), int(match.group(2))) if match else None
        # these read "<ported> of the <total>"
        check(f"{name}: ported panels", got, (MIGRATED, DOCKS))

print("FAILURES:", failures)
sys.exit(1 if failures else 0)
