# =============================================================================
# HYDRA-UMC SUITE - panel_logic/ecosystem_map.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The map of the ecosystem without any window toolkit: the projects that GET /api/ecosystem/status reports (a scan of the manifests
# next to the server plus a probe of the ones that declare a service), grouped by family, each one reduced to the state a person needs
# to see on a map (up, in error, down, unknown), with the totals, a search and a filter by state. A project whose version differs from
# the one its manifest expects is marked when the health of the ecosystem is on (an administrator turns it on in Server Admin); without
# it the map simply shows no drift. A switch (off until turned on) adds to every tile what the project has been tried on (nothing
# recorded, a computer, a simulator, the bench, real hardware) and its open gaps, from the snapshot in assets/maturity_ledger.json,
# which says what was done and never more. The same reading as the Map of HYDRA-UMC STUDIO. Read only.
# =============================================================================
from __future__ import annotations

import json
from pathlib import Path

from hydra_suite.i18n import _

MAP_STATES = ("up", "error", "down", "unknown")
FILTERS = ("all", *MAP_STATES)
POLL_MS = 20000
LEDGER_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "maturity_ledger.json"
EVIDENCE_COLOURS = {"neutral": "#7f8ea1", "info": "#6cc3ff", "warn": "#f0b45a", "ok_soft": "#b7e36b", "ok": "#4fd08a"}
STATE_COLOURS = {"up": "#4fd08a", "error": "#f0b45a", "down": "#ee6b80", "unknown": "#556070"}
#: The names of the interface languages (hydra_suite/i18n.py) and the codes the maturity ledger uses for its labels.
LANGUAGE_CODES = {
    "english": "en", "spanish": "es", "german": "de", "french": "fr", "italian": "it", "japanese": "ja", "chinese": "zh", "portuguese": "pt",
}


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def parse_project(raw: object) -> dict | None:
    """One project of the answer; whatever is damaged is dropped (a project with no name is dropped altogether)."""
    if not isinstance(raw, dict) or not _text(raw.get("name")):
        return None
    port = raw.get("servicePort")
    live = raw.get("live")
    return {
        "name": raw["name"],
        "role": _text(raw.get("role")),
        "stack": _text(raw.get("stack")),
        "maturity": _text(raw.get("maturity")),
        "family": _text(raw.get("family")),
        "version": _text(raw.get("version")),
        "servicePort": port if isinstance(port, int) and not isinstance(port, bool) else None,
        "activeState": _text(raw.get("activeState")),
        "live": live if isinstance(live, bool) else None,
    }


def parse_projects(raw: object) -> list[dict]:
    return [p for p in (parse_project(item) for item in raw) if p is not None] if isinstance(raw, list) else []


def state_of(project: dict) -> str:
    """A failed unit, or an active one whose own port does not answer, is an error; otherwise the probe or the unit decide."""
    active, live = project.get("activeState"), project.get("live")
    if active == "failed":
        return "error"
    if active == "active":
        return "error" if live is False else "up"
    if active:
        return "down"
    if live is True:
        return "up"
    if live is False:
        return "down"
    return "unknown"


def summarize(projects: list[dict]) -> dict[str, int]:
    counts = {"all": len(projects), **{state: 0 for state in MAP_STATES}}
    for project in projects:
        counts[state_of(project)] += 1
    return counts


def search_projects(projects: list[dict], query: str) -> list[dict]:
    """Only the projects whose name, family, role or stack contains every word (case-insensitive); an empty search keeps all."""
    words = query.lower().split()
    if not words:
        return list(projects)
    kept = []
    for project in projects:
        haystack = " ".join(str(project[key]) for key in ("name", "family", "role", "stack") if project.get(key)).lower()
        if all(word in haystack for word in words):
            kept.append(project)
    return kept


def group_by_family(projects: list[dict]) -> list[tuple[str | None, list[dict]]]:
    """The families in alphabetical order with the projects without family last, and the projects of each by name."""
    groups: dict[str | None, list[dict]] = {}
    for project in projects:
        groups.setdefault(project["family"], []).append(project)
    ordered = sorted(groups, key=lambda family: (family is None, (family or "").lower()))
    return [(family, sorted(groups[family], key=lambda p: p["name"].lower())) for family in ordered]


# -- the maturity ledger ----------------------------------------------------


def parse_ledger(raw: object) -> dict:
    """The kinds of evidence (identifier, colour, labels per language) and the entry of each project; whatever is malformed is dropped."""
    ledger: dict = {"kinds": {}, "entries": {}}
    if not isinstance(raw, dict):
        return ledger
    for kind in raw.get("evidence_kinds") if isinstance(raw.get("evidence_kinds"), list) else []:
        if isinstance(kind, dict) and isinstance(kind.get("id"), str) and kind.get("colour") in EVIDENCE_COLOURS:
            labels = kind.get("label")
            ledger["kinds"][kind["id"]] = {"colour": kind["colour"], "label": {k: v for k, v in labels.items() if isinstance(v, str)} if isinstance(labels, dict) else {}}
    for repo in raw.get("repos") if isinstance(raw.get("repos"), list) else []:
        if isinstance(repo, dict) and isinstance(repo.get("name"), str) and repo.get("evidence") in ledger["kinds"]:
            gaps = repo.get("gaps")
            ledger["entries"][repo["name"]] = {"evidence": repo["evidence"], "gaps": [g for g in gaps if isinstance(g, str)] if isinstance(gaps, list) else []}
    return ledger


def load_ledger(path: Path = LEDGER_PATH) -> dict:
    try:
        return parse_ledger(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return parse_ledger(None)


LEDGER = load_ledger()


def evidence_for(ledger: dict, name: str, language: str) -> dict | None:
    """What a project has been tried on, in the words of the interface language (English, then the identifier, when a label is missing)."""
    entry = ledger["entries"].get(name)
    if entry is None:
        return None
    kind = ledger["kinds"][entry["evidence"]]
    code = LANGUAGE_CODES.get(language, "en")
    label = kind["label"].get(code) or kind["label"].get("en") or entry["evidence"]
    return {"id": entry["evidence"], "label": label, "colour": EVIDENCE_COLOURS[kind["colour"]], "gaps": len(entry["gaps"])}


# -- what the screen shows ----------------------------------------------------


def filter_rows(projects: list[dict], selected: str) -> list[dict]:
    counts = summarize(projects)
    return [{"key": key, "label": f"{_('ECOMAP_ALL') if key == 'all' else _('ECOMAP_STATE_' + key.upper())} {counts[key]}", "selected": key == selected,
             "colour": "" if key == "all" else STATE_COLOURS[key]} for key in FILTERS]


def tile_row(project: dict, drifting: set[str], show_evidence: bool, language: str, ledger: dict | None = None) -> dict:
    state = state_of(project)
    evidence = evidence_for(LEDGER if ledger is None else ledger, project["name"], language) if show_evidence else None
    details = [part for part in (f"v{project['version']}" if project["version"] else "-", f":{project['servicePort']}" if project["servicePort"] is not None else "",
                                 project["maturity"] or "", project["stack"] or "") if part]
    return {
        "name": project["name"],
        "short": project["name"].removeprefix("HYDRA-UMC-"),
        "details": " ".join(details),
        "state": state,
        "stateLabel": _("ECOMAP_STATE_" + state.upper()),
        "colour": STATE_COLOURS[state],
        "drift": project["name"] in drifting,
        "driftLabel": _("ECOMAP_DRIFT") if project["name"] in drifting else "",
        "evidence": "" if evidence is None else evidence["label"] + (" - " + _("ECOMAP_EVIDENCE_GAPS", count=evidence["gaps"]) if evidence["gaps"] else ""),
        "evidenceColour": "" if evidence is None else evidence["colour"],
    }


def family_rows(projects: list[dict], selected: str, query: str, drifting: set[str], show_evidence: bool, language: str, ledger: dict | None = None) -> list[dict]:
    """The families with their tiles, after the search and the filter by state."""
    shown = [p for p in search_projects(projects, query) if selected == "all" or state_of(p) == selected]
    return [
        {"family": family or _("ECOMAP_FAMILY_OTHER"), "count": len(items), "tiles": [tile_row(p, drifting, show_evidence, language, ledger) for p in items]}
        for family, items in group_by_family(shown)
    ]


def drifting_names(health: dict | None) -> set[str]:
    """The names of the services that report another version than their manifest, from the parsed health of the ecosystem (or none)."""
    return {s["name"] for s in health["services"] if s.get("drift")} if isinstance(health, dict) and isinstance(health.get("services"), list) else set()
