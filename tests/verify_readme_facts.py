# =============================================================================
# HYDRA-UMC SUITE - tests/verify_readme_facts.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The numbers the READMEs state must be the real ones, in the eight languages:
#   - how many offline verify scripts there are under tests/
#   - how many panels the navigation of the interface has
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

from hydra_suite.nav_items import ALL_DOCK_KEYS

PANELS_COUNT = len(set(ALL_DOCK_KEYS))

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
    "README.md": r"all (\d+) panels of the navigation",
    "README_deu.md": r"alle (\d+) Panels der Navigation",
    "README_fra.md": r"les (\d+) panneaux de la navigation",
    "README_ita.md": r"tutti i (\d+) pannelli della navigazione",
    "README_jpn.md": r"ナビゲーションの全 (\d+) パネル",
    "README_por.md": r"os (\d+) painéis da navegação",
    "README_spa.md": r"los (\d+) paneles de la navegación",
    "README_zho.md": r"导航中的全部 (\d+) 个面板",
}

check("there are verify scripts", VERIFIERS > 0, True)
check("the navigation has panels", PANELS_COUNT > 0, True)
for name, pattern in COUNT.items():
    text = (ROOT / name).read_text(encoding="utf-8")
    match = re.search(pattern, text)
    check(f"{name}: verify script count", int(match.group(1)) if match else None, VERIFIERS)
for name, pattern in PANELS.items():
    text = (ROOT / name).read_text(encoding="utf-8")
    match = re.search(pattern, text)
    check(f"{name}: panels of the navigation", int(match.group(1)) if match else None, PANELS_COUNT)

print("FAILURES:", failures)
sys.exit(1 if failures else 0)
