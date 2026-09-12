# =============================================================================
# HYDRA-UMC-SUITE - Heated bed preset and footprint contract
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import json
from pathlib import Path

CATALOG_DIR = Path(__file__).resolve().parent.parent / "assets" / "meshes" / "heated-beds"
_catalog = json.loads((CATALOG_DIR / "catalog.json").read_text(encoding="utf-8"))
HEATED_BED_MODELS = _catalog["models"]


def heated_bed_model(model_id=None):
    return next((m for m in HEATED_BED_MODELS if m["id"] == model_id),
                next(m for m in HEATED_BED_MODELS if m["id"] == _catalog["defaultModelId"]))


def _valid(n):
    return type(n) in (int, float) and 25 <= n <= 5000 and int(n) == n


def heated_bed_size(module):
    model = heated_bed_model(module.get("modelId"))
    size = module.get("size")
    size = size if isinstance(size, dict) else {}
    return {axis: size[axis] if _valid(size.get(axis)) else model[axis] for axis in ("width", "length")}


def select_heated_bed(module, model_id):
    model = next((m for m in HEATED_BED_MODELS if m["id"] == model_id), None)
    return {**module, "modelId": model_id, "size": {"width": model["width"], "length": model["length"]}} if model else dict(module)


def resize_heated_bed(module, axis, value):
    if axis not in ("width", "length") or not _valid(value):
        return dict(module)
    return {**module, "size": {**heated_bed_size(module), axis: value}}
