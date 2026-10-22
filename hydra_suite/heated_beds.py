# =============================================================================
# HYDRA-UMC-SUITE - Heated bed preset and footprint contract
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import json
from pathlib import Path

CATALOG_DIR = Path(__file__).resolve().parent.parent / "assets" / "meshes" / "heatedbeds" / "default"
_FALLBACK_MODEL = {"id": "200x200x5", "label": "200 x 200 x 5 mm", "width": 200, "length": 200, "totalHeight": 5, "file": ""}


def _load_catalog(directory=CATALOG_DIR) -> dict:
    """The catalog file, or a one-model fallback when it is missing, unreadable
    or malformed: a damaged asset must not stop the program from starting."""
    try:
        data = json.loads((Path(directory) / "catalog.json").read_text(encoding="utf-8"))
        models = [m for m in data["models"] if isinstance(m, dict) and "id" in m and "width" in m and "length" in m]
        if models:
            default = data.get("defaultModelId")
            return {"models": models, "defaultModelId": default if any(m["id"] == default for m in models) else models[0]["id"]}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return {"models": [dict(_FALLBACK_MODEL)], "defaultModelId": _FALLBACK_MODEL["id"]}


_catalog = _load_catalog()
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
