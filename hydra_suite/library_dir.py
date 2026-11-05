# =============================================================================
# HYDRA-UMC SUITE - library_dir.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# One folder for the 3D model library of the two apps. STUDIO serves `public/models` and this app reads `assets/meshes`: the same
# layout (category / model / files). When HYDRA_UMC_LIBRARY_DIR names an existing folder, this app reads the models from it, and so do
# STUDIO and the STL editor, so a model is edited in one place. Unset (the default), or naming something that is not a folder, this app
# keeps reading its own `assets/meshes`: a wrong value never points the app at an unexpected place.
# Standard library only.
# =============================================================================
from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

LIBRARY_DIR_ENV = "HYDRA_UMC_LIBRARY_DIR"


def shared_dir(environ: Mapping[str, str] | None = None) -> Path | None:
    """The common library folder, or None when the variable is unset or does not name an existing folder."""
    value = (os.environ if environ is None else environ).get(LIBRARY_DIR_ENV, "").strip()
    if not value:
        return None
    candidate = Path(value).expanduser()
    return candidate if candidate.is_dir() else None


def mesh_root(default: Path, environ: Mapping[str, str] | None = None) -> Path:
    """The folder the models are read from: the common library folder when there is one, else `default` (this app's `assets/meshes`)."""
    return shared_dir(environ) or default
