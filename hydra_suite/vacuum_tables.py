# =============================================================================
# HYDRA-UMC-SUITE - Vacuum table catalog and selection contract
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json
from pathlib import Path

CATALOG_DIR = Path(__file__).resolve().parent.parent / "assets" / "meshes" / "vacuum-tables"
VACUUM_TABLE_MODELS = json.loads((CATALOG_DIR / "catalog.json").read_text(encoding="utf-8"))["models"]


def vacuum_table_model(model_id=None) -> dict:
    """Unknown/legacy IDs use the first model for display, without rewriting state."""
    return next((m for m in VACUUM_TABLE_MODELS if m["id"] == model_id), VACUUM_TABLE_MODELS[0])


def select_vacuum_table(module: dict, model_id: str) -> dict:
    """Whitelist IDs and preserve pump/valve, placement and extension fields."""
    model = next((m for m in VACUUM_TABLE_MODELS if m["id"] == model_id), None)
    if model is None:
        return dict(module)
    return {**module, "customSize": False, "modelId": model["id"], "size": {"width": model["width"], "length": model["length"]}}


def vacuum_table_size(module: dict) -> dict:
    """Only explicit custom sizes override the catalog; reject malformed dimensions."""
    model = vacuum_table_model(module.get("modelId"))
    size = module.get("size")
    size = size if isinstance(size, dict) else {}
    def dimension(axis):
        n = size.get(axis)
        return n if module.get("customSize") is True and type(n) in (int, float) and 10 <= n <= 5000 and int(n) == n else model[axis]
    return {axis: dimension(axis) for axis in ("width", "length")}


def resize_vacuum_table(module: dict, axis: str, value: int) -> dict:
    """Changing a dimension never changes placement or physical control fields."""
    if axis not in ("width", "length") or type(value) not in (int, float) or not 10 <= value <= 5000 or int(value) != value:
        return dict(module)
    return {**module, "customSize": True, "size": {**vacuum_table_size(module), axis: value}}
