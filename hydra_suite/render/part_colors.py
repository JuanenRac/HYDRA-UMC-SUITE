# =============================================================================
# HYDRA-UMC SUITE - render/part_colors.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real per-part color overrides, saved by the separate HYDRA-UMC-EDITOR-STL
# desktop tool as a sidecar `part_colors.json` file next to a model's own
# STL parts (see that repo's own part_colors.py - a flat
# `{"<filename>": "#rrggbb"}` dict, only listing parts that actually have a
# saved color). Until this module existed, that annotation was an
# EDITOR-STL-only preview with no effect anywhere else - this is the one
# place SUITE's own live 3D viewport reads it back (viewport.py/
# module_rig.py), read-only (SUITE never writes this file, only EDITOR-STL
# does), matching HYDRA-UMC-STUDIO's own hooks/usePartColors.ts.
# =============================================================================
from __future__ import annotations

import json
from pathlib import Path

COLORS_FILENAME = "part_colors.json"


def load_part_colors(model_dir: Path) -> dict[str, str]:
    """Real, on-disk colors for this model's own parts - `{}` (never an
    error) if the sidecar file doesn't exist yet or fails to parse, since
    "no colors saved yet" is a normal, honest starting state, not a
    failure. Same tolerant shape as EDITOR-STL's own load_part_colors()."""
    path = model_dir / COLORS_FILENAME
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if isinstance(v, str)}


def hex_to_rgb01(hex_color: str) -> tuple[float, float, float] | None:
    """`"#rrggbb"` -> `(r, g, b)` floats in 0..1, this renderer's own real
    color format (see viewport.py's `uBaseColor` uniform) - `None` for
    anything that isn't a real 6-digit hex color, so a corrupt/hand-edited
    sidecar entry falls back to the caller's own default instead of
    crashing the viewport."""
    if not (isinstance(hex_color, str) and len(hex_color) == 7 and hex_color.startswith("#")):
        return None
    try:
        r = int(hex_color[1:3], 16) / 255.0
        g = int(hex_color[3:5], 16) / 255.0
        b = int(hex_color[5:7], 16) / 255.0
    except ValueError:
        return None
    return (r, g, b)
