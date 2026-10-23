# =============================================================================
# HYDRA-UMC SUITE - panel_logic/admin_logs.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The values and helpers of the admin logs panel that do not depend on any window toolkit: the Qt Quick
# interface and the checks use them directly.
# =============================================================================
from __future__ import annotations

import re


_TAG_RE = re.compile(r"\[([A-Za-z0-9_-]+)]")


def _extract_tag(line: str) -> str | None:
    m = _TAG_RE.search(line)
    return m.group(1) if m else None
