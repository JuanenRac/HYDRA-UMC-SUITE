# =============================================================================
# HYDRA-UMC SUITE - tests/verify_ecosystem_map.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The Map of the ecosystem, without a window and without a network:
#   - the state of a project from its unit and its probe (a failed unit or an active one whose port does not answer is an error)
#   - the totals, the search, the filter by state and the families in order, those without a family last
#   - a damaged project is dropped, not the rest
#   - the drift mark comes from the health of the ecosystem and is absent without it
#   - the evidence of the maturity ledger only appears when the switch is on, in the language of the interface, with its gaps
#   - the copy of the ledger in assets/ is the one of the documentation hub when that is checked out next to this repository
#   - every sentence the screen shows exists in the eight languages
# Run headless: no Qt is needed.
# =============================================================================
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hydra_suite.i18n import LANGUAGE_FOLDER
from hydra_suite.panel_logic import ecosystem_map as em

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def project(name, **values):
    return em.parse_project({"name": name, **values})


def logic():
    check("a failed unit is an error", em.state_of(project("a", activeState="failed")), "error")
    check("an active unit whose port does not answer is an error", em.state_of(project("a", activeState="active", live=False)), "error")
    check("an active unit is up", em.state_of(project("a", activeState="active")), "up")
    check("an inactive unit is down", em.state_of(project("a", activeState="inactive")), "down")
    check("a probe that answers is up", em.state_of(project("a", live=True)), "up")
    check("a probe that does not answer is down", em.state_of(project("a", live=False)), "down")
    check("nothing known is unknown", em.state_of(project("a")), "unknown")

    projects = em.parse_projects([
        {"name": "HYDRA-UMC-SERVER", "family": "core", "version": "1.0.0", "servicePort": 3000, "activeState": "active", "stack": "node"},
        {"name": "HYDRA-UMC-TWIN", "family": "core", "live": False},
        {"name": "HYDRA-UMC-APP", "family": "apps", "activeState": "failed"},
        {"name": "NO-FAMILY"},
        {"name": ""},
        "damaged",
        {"name": "BAD-PORT", "family": "apps", "servicePort": True},
    ])
    check("a damaged project is dropped, not the rest", [p["name"] for p in projects], ["HYDRA-UMC-SERVER", "HYDRA-UMC-TWIN", "HYDRA-UMC-APP", "NO-FAMILY", "BAD-PORT"])
    check("a boolean is not a port", projects[-1]["servicePort"], None)
    check("an answer that is not a list gives no projects", em.parse_projects({"projects": 1}), [])
    check("the totals", em.summarize(projects), {"all": 5, "up": 1, "error": 1, "down": 1, "unknown": 2})
    check("the search keeps every word", [p["name"] for p in em.search_projects(projects, "core node")], ["HYDRA-UMC-SERVER"])
    check("an empty search keeps all", len(em.search_projects(projects, "  ")), 5)
    groups = em.group_by_family(projects)
    check("families in order, those without one last", [family for family, _items in groups], ["apps", "core", None])
    check("projects of a family by name", [p["name"] for p in groups[0][1]], ["BAD-PORT", "HYDRA-UMC-APP"])

    rows = em.family_rows(projects, "all", "", {"HYDRA-UMC-TWIN"}, False, "english")
    tiles = {t["name"]: t for family in rows for t in family["tiles"]}
    check("a tile carries the short name and the details", (tiles["HYDRA-UMC-SERVER"]["short"], tiles["HYDRA-UMC-SERVER"]["details"]), ("SERVER", "v1.0.0 :3000 node"))
    check("the drift mark only where the health says so", [name for name, t in tiles.items() if t["drift"]], ["HYDRA-UMC-TWIN"])
    check("no evidence while the switch is off", {t["evidence"] for t in tiles.values()}, {""})
    check("the filter by state", [t["name"] for f in em.family_rows(projects, "error", "", set(), False, "english") for t in f["tiles"]], ["HYDRA-UMC-APP"])
    check("the other family is named", rows[-1]["family"], em._("ECOMAP_FAMILY_OTHER"))

    check("no drift without the health", em.drifting_names(None), set())
    check("the drift comes from the services of the health", em.drifting_names({"services": [{"name": "a", "drift": True}, {"name": "b", "drift": False}]}), {"a"})


def evidence():
    ledger = em.parse_ledger({
        "evidence_kinds": [
            {"id": "none", "colour": "neutral", "label": {"en": "No evidence", "es": "Sin evidencia"}},
            {"id": "bench", "colour": "ok_soft", "label": {"en": "Tried on the bench"}},
            {"id": "odd", "colour": "purple", "label": {"en": "unknown colour"}},
        ],
        "repos": [
            {"name": "A", "evidence": "none", "gaps": ["x", "y", 3]},
            {"name": "B", "evidence": "bench"},
            {"name": "C", "evidence": "odd"},
            {"name": "D", "evidence": "missing"},
            "damaged",
        ],
    })
    check("only the known kinds and projects stay", (sorted(ledger["kinds"]), sorted(ledger["entries"])), (["bench", "none"], ["A", "B"]))
    a = em.evidence_for(ledger, "A", "spanish")
    check("the label is in the language of the interface, with the gaps counted", (a["label"], a["gaps"]), ("Sin evidencia", 2))
    check("a missing label falls back to English", em.evidence_for(ledger, "B", "german")["label"], "Tried on the bench")
    check("a project that is not in the ledger has no line", em.evidence_for(ledger, "Z", "english"), None)
    shown = em.tile_row(project("A"), set(), True, "english", ledger)
    check("the tile shows what was tried and the gaps when the switch is on", shown["evidence"].startswith("No evidence - "), True)
    check("and nothing when it is off", em.tile_row(project("A"), set(), False, "english", ledger)["evidence"], "")

    real = em.LEDGER
    check("the real ledger has kinds and projects", (len(real["kinds"]) > 0, len(real["entries"]) > 0), (True, True))
    docs = ROOT.parent / "HYDRA-UMC-DOCS" / "data" / "maturity_ledger.json"
    if docs.exists():
        check("the copy of the ledger is the one of the documentation hub", (ROOT / "assets" / "maturity_ledger.json").read_bytes().replace(b"\r\n", b"\n"), docs.read_bytes().replace(b"\r\n", b"\n"))
    else:
        print("skip the comparison with the documentation hub (not checked out next to this repository)")


def sentences():
    source = (ROOT / "hydra_suite" / "panel_logic" / "ecosystem_map.py").read_text(encoding="utf-8")
    keys = {k for k in re.findall(r"_\(['\"](ECOMAP_[A-Z_]+)", source) if not k.endswith("_")} | {f"ECOMAP_STATE_{s.upper()}" for s in em.MAP_STATES}
    qml = (ROOT / "assets" / "qml" / "Main.qml").read_text(encoding="utf-8")
    keys |= set(re.findall(r'uiText\("((?:ECOMAP_|DOCK_ECOSYSTEM_MAP)[A-Z_]*)"', qml))
    check("the screen uses sentences", len(keys) >= 14, True)
    for lng in sorted(LANGUAGE_FOLDER.glob("*.lng")):
        have = {line.split("=", 1)[0] for line in lng.read_text(encoding="utf-8").splitlines() if "=" in line}
        check(f"{lng.name} has every sentence of the map", sorted(keys - have), [])
    check("the map is in the navigation", "ecosystem_map" in __import__("hydra_suite.nav_items", fromlist=["ALL_DOCK_KEYS"]).ALL_DOCK_KEYS, True)


def main() -> int:
    logic()
    evidence()
    sentences()
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
