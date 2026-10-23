# =============================================================================
# HYDRA-UMC SUITE - panel_logic/cameras.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The values and helpers of the cameras panel that do not depend on any window toolkit: the Qt Quick
# interface and the checks use them directly.
# =============================================================================
from __future__ import annotations

import httpx
from collections.abc import AsyncIterator
from hydra_suite.models import CAMERA_TYPES


# type strings for the USB-only and Thermal option groups, mirroring
# HYDRA-UMC-STUDIO's own CamerasView.tsx combobox split. The IP group is
# NOT a fixed pair here - see ip_stream_labels() in models.py, used
# directly wherever this panel needs the real, per-camera IP option
# list instead.
_USB_TYPE_OPTIONS = (CAMERA_TYPES[0],)


_THERMAL_TYPE_OPTIONS = CAMERA_TYPES[3:]


# Real camera-process status colors, matching HYDRA-UMC-STUDIO's own
# Config.tsx badge coloring for the exact same 3 states HYDRA-UMC-SERVER's
# own GET /api/cameras/status can report (see that route's own comment).
_STATUS_COLORS = {"running": "#10b981", "starting": "#f59e0b", "error": "#ef4444", "stopped": "#8a97a6"}


GRID_COLUMNS = 4


# Max single JPEG frame this reader accepts before treating it as
# corrupt and resyncing to the next SOI - matches
# HYDRA-UMC-ANDROID-CONTROL's own MjpegStreamParser.kt exactly (same
# real 1MB ceiling, same "keep the socket, resync instead of dropping
# the whole connection over one oversized frame" reasoning).
_MJPEG_MAX_FRAME_BYTES = 1024 * 1024


_JPEG_SOI = b"\xff\xd8"


_JPEG_EOI = b"\xff\xd9"


async def iter_mjpeg_frames(url: str, headers: dict[str, str] | None = None) -> AsyncIterator[bytes]:
    """Real MJPEG multipart/x-mixed-replace client - reads raw bytes off
    the wire and scans for JPEG SOI(0xFFD8)/EOI(0xFFD9) markers directly,
    the same real, proven approach HYDRA-UMC-ANDROID-CONTROL's own
    MjpegStreamParser.kt uses (see that file's own header) - deliberately
    NOT parsing the multipart boundary/Content-Length headers at all,
    since the marker scan already works regardless of exact framing and
    is what the one other real client in this ecosystem already does.
    Yields one complete, real JPEG frame's raw bytes at a time; ends
    (StopAsyncIteration) on a genuine connection close/error - never
    raises out of this generator, so a caller's own `async for` loop
    doesn't need its own try/except around iteration itself."""
    try:
        # `headers` carries the session's bearer token: a server started with
        # HYDRA_UMC_CAMERA_AUTH=required refuses the picture without it.
        async with httpx.AsyncClient(headers=headers) as client:
            async with client.stream("GET", url, timeout=httpx.Timeout(10.0, read=None)) as resp:
                if resp.status_code != 200:
                    return
                buffer = bytearray()
                async for chunk in resp.aiter_bytes():
                    buffer.extend(chunk)
                    while True:
                        start = buffer.find(_JPEG_SOI)
                        if start < 0:
                            # No SOI at all yet - drop everything except a
                            # possible trailing 0xFF (could be the first
                            # byte of a SOI split across chunks).
                            if buffer and buffer[-1] == 0xFF:
                                del buffer[:-1]
                            else:
                                buffer.clear()
                            break
                        end = buffer.find(_JPEG_EOI, start + 2)
                        if end < 0:
                            # Frame not complete yet. If what we're
                            # accumulating already exceeds the real cap,
                            # drop the leading SOI so a genuinely
                            # oversized/corrupt frame can't grow the
                            # buffer forever - the next chunk's own scan
                            # then looks for a fresh SOI instead.
                            if len(buffer) - start > _MJPEG_MAX_FRAME_BYTES:
                                del buffer[: start + 2]
                                continue
                            del buffer[:start]
                            break
                        frame = bytes(buffer[start : end + 2])
                        del buffer[: end + 2]
                        if len(frame) <= _MJPEG_MAX_FRAME_BYTES:
                            yield frame
                        # else: corrupt/oversized frame, silently skipped -
                        # matches MjpegFrameResult.CorruptFrame's own
                        # "keep reading, don't kill the feed" behavior.
    except (httpx.HTTPError, OSError):
        return
