# =============================================================================
# HYDRA-UMC SUITE - panel_logic/camera_media.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The values and helpers of the camera media panel that do not depend on any window toolkit: the Qt Quick
# interface and the checks use them directly.
# =============================================================================
from __future__ import annotations

_JPEG_SOI = b"\xff\xd8"


_JPEG_EOI = b"\xff\xd9"


def parse_mjpeg_frames(data: bytes) -> list[bytes]:
    """Real, synchronous parse of a fully-downloaded .mjpeg recording's
    own bytes into an ordered list of real JPEG frame byte strings - same
    SOI/EOI marker-scan approach as the former cameras panel's
    iter_mjpeg_frames() (proven against this exact real wire format
    already), just over an in-memory blob instead of a live stream.
    Never raises on malformed/truncated input - a partial trailing frame
    with no real EOI yet is simply not included, matching a recording
    that was cut off mid-frame."""
    frames: list[bytes] = []
    offset = 0
    while True:
        start = data.find(_JPEG_SOI, offset)
        if start < 0:
            break
        end = data.find(_JPEG_EOI, start + 2)
        if end < 0:
            break
        frames.append(data[start : end + 2])
        offset = end + 2
    return frames
