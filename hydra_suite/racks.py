# =============================================================================
# HYDRA-UMC-SUITE - Rack geometry contract, millimeters and fixed slot pitch
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import re
from pathlib import Path

ASSET_DIR = Path(__file__).resolve().parent.parent / "assets" / "meshes" / "racks"


def valid_dimension(v):
    return type(v) in (int, float) and 40 <= v <= 1000 and int(v) == v


def valid_color(v):
    return isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v) is not None


def rack_geometry(rack):
    n = rack.get("capacity")
    color = rack.get("color")
    return {
        "width": rack["width"] if valid_dimension(rack.get("width")) else 160,
        "depth": rack["depth"] if valid_dimension(rack.get("depth")) else 160,
        "capacity": int(n) if type(n) in (int, float) and 1 <= n <= 24 and int(n) == n else 24,
        "color": color if valid_color(color) else ("#10b981" if rack.get("type") == "Output" else "#0ea5e9"),
    }


def rack_parts(rack):
    g = rack_geometry(rack)
    w, d, n = g["width"], g["depth"], g["capacity"]
    h = n * 10 + 40
    parts = [("base", (w+20, 20, d+20), (0, 10, 0))]
    for side in (-1, 1):
        parts.append(("wall", (10, h, d), (side*(w/2+5), h/2, 0)))
        for i in range(n):
            parts.append(("guide", (4, 3, d), (side*(w/2-2), 37.5+i*10, 0)))
    return parts
