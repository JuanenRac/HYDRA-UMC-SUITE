# =============================================================================
# HYDRA-UMC SUITE - panel_logic/submitted_models.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The models the editors (HYDRA-UMC-EDITOR-URDF, HYDRA-UMC-EDITOR-STL) submitted to the server, without any window
# toolkit: GET /api/models lists them and GET /api/models/:category/:slug/download gives the URDF and the meshes of
# one. Everything that comes from the server is read defensively: an entry that is not a model is skipped, a name
# that would be a path is never used as a file name.
# =============================================================================
from __future__ import annotations

import re
import urllib.parse

from hydra_suite.i18n import _

_PLAIN_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,127}$")


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def parse_models(body: object) -> list[dict[str, str]]:
    """The models of a GET /api/models answer, newest first and then by name; anything else is an empty list."""
    listed = body.get("models") if isinstance(body, dict) else None
    if not isinstance(listed, list):
        return []
    out: list[dict[str, str]] = []
    for item in listed:
        if not isinstance(item, dict):
            continue
        slug, category = _text(item.get("slug")), _text(item.get("category"))
        if slug is None or category is None:
            continue
        out.append({"slug": slug, "category": category, "name": _text(item.get("name")) or slug, "submittedAt": _text(item.get("submittedAt")) or ""})
    out.sort(key=lambda m: m["name"].lower())
    out.sort(key=lambda m: m["submittedAt"], reverse=True)
    return out


def rows(models: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "name": m["name"],
            "category": m["category"],
            "slug": m["slug"],
            "submitted": m["submittedAt"].replace("T", " ").rsplit(".", 1)[0].rstrip("Z") if m["submittedAt"] else "-",
        }
        for m in models
    ]


def download_path(category: str, slug: str) -> str:
    """The path of the download of one model (every part is encoded, so a name cannot add a segment)."""
    return f"/api/models/{urllib.parse.quote(category, safe='')}/{urllib.parse.quote(slug, safe='')}/download"


def urdf_file_name(answer: object, slug: str) -> str:
    """The name the URDF is saved under: the one the server gave when it is one plain name, otherwise `<slug>.urdf`."""
    given = answer.get("urdfFilename") if isinstance(answer, dict) else None
    base = re.split(r"[\\/]", given)[-1] if isinstance(given, str) else ""
    if _PLAIN_NAME.match(base) and base.lower().endswith(".urdf"):
        return base
    return (slug if _PLAIN_NAME.match(slug) else "model") + ".urdf"


def urdf_text(answer: object) -> str | None:
    xml = answer.get("urdfXml") if isinstance(answer, dict) else None
    return xml if isinstance(xml, str) and xml.strip() else None


def failure_text(status: int) -> str:
    """Why the list could not be read, as a sentence (status 0: the server did not answer)."""
    if status == 0:
        return _("MODELS_ERROR_NETWORK")
    if status in (401, 403):
        return _("MODELS_ERROR_LOGIN")
    return _("MODELS_ERROR_SERVER")
