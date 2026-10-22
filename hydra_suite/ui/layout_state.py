# =============================================================================
# HYDRA-UMC SUITE - layout_state.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The arrangement of the docks (which panel is where, which ones are closed or
# floating) is kept in the configuration file between sessions. The dock state
# Qt gives back is binary; it is stored as base64 text next to a format
# version so a file written by another version, edited by hand or damaged is
# ignored instead of breaking the start-up. Pure functions, no Qt window.
# =============================================================================
from __future__ import annotations

import base64
import binascii

CONFIG_KEY = "dock_layout"
LAYOUT_VERSION = 1
# A real dock state is a few kilobytes; anything far larger is not one.
_MAX_STATE_BYTES = 256 * 1024


def encode_layout(state: bytes) -> dict:
    """The value stored under CONFIG_KEY for a dock state returned by saveState()."""
    return {"version": LAYOUT_VERSION, "state": base64.b64encode(bytes(state)).decode("ascii")}


def decode_layout(value: object) -> bytes | None:
    """The dock state to hand to restoreState(), or None when the stored value
    is missing, from another format version or not valid base64."""
    if not isinstance(value, dict) or value.get("version") != LAYOUT_VERSION:
        return None
    text = value.get("state")
    if not isinstance(text, str) or not text or len(text) > _MAX_STATE_BYTES * 2:
        return None
    try:
        state = base64.b64decode(text.encode("ascii"), validate=True)
    except (binascii.Error, ValueError, UnicodeEncodeError):
        return None
    if not state or len(state) > _MAX_STATE_BYTES:
        return None
    return state
