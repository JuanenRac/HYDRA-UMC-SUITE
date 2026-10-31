# =============================================================================
# HYDRA-UMC-SUITE - tests/test_rest_routes.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Fixes the list of server routes this app calls.

A route can only be added or dropped on purpose (update `tests/fixtures/rest_routes.json`), and when the shared contracts are
checked out next to this repository every route must exist in the server contract.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "rest_routes.json"
CONTRACT = ROOT.parent / "HYDRA-UMC-SDK" / "contracts" / "openapi" / "v1" / "server.full.openapi.json"
LITERAL = re.compile(r"""["'](/api/[^"'\s]*)["']""")


def called_routes() -> list[str]:
    """Every `/api/...` literal in the sources, with format fields shown as `{p}` and any query string removed."""
    found: set[str] = set()
    sources = list((ROOT / "hydra_suite").rglob("*.py")) + [ROOT / "qt_suite.py"]
    for path in sources:
        for match in LITERAL.finditer(path.read_text(encoding="utf-8")):
            route = re.sub(r"\{[^}]*\}", "{p}", match.group(1)).split("?")[0].rstrip("/")
            if len(route) > 5:
                found.add(route)
    return sorted(found)


def test_routes_match_the_recorded_list():
    assert called_routes() == json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.mark.skipif(not CONTRACT.exists(), reason="the shared contracts are not checked out next to this repository")
def test_routes_exist_in_the_server_contract():
    paths = list(json.loads(CONTRACT.read_text(encoding="utf-8"))["paths"])

    def matches(route: str, path: str) -> bool:
        return re.fullmatch(route.replace("{p}", "[^/]+"), re.sub(r"\{[^}]+\}", "x", path)) is not None

    unknown = [r for r in called_routes() if not any(matches(r, p) for p in paths)]
    assert unknown == []
