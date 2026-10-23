# =============================================================================
# HYDRA-UMC SUITE - panel_logic/server_browser.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The values and helpers of the server browser panel that do not depend on any window toolkit: the Qt Quick
# interface and the checks use them directly.
# =============================================================================
from __future__ import annotations

STATUS_DISPLAY_KEYS = {
    "connected": "STATUS_CONNECTED",
    "connecting": "STATUS_CONNECTING",
    "disconnected": "STATUS_DISCONNECTED",
    "error": "STATUS_ERROR",
    # Distinct from "error" on purpose - a WebSocket link that dropped and a
    # server that flat-out rejected the configured username/password are
    # different problems with different fixes (wait/retry vs. edit
    # credentials); collapsing both into the same generic "Error" would make
    # them indistinguishable from this table alone.
    "login_failed": "STATUS_LOGIN_FAILED",
}
