# =============================================================================
# HYDRA-UMC SUITE - hydra_suite/panel_logic/watch_notice.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""What the phones told the server about telling their watch of a newer release (read only; the switch is on each phone)."""
from __future__ import annotations


def parse_devices(result: tuple[int, object] | None) -> list[dict] | None:
    """The devices of the answer of GET /api/admin/watch/release-notice; None when the server has no such route or the answer is not usable."""
    if result is None or result[0] != 200 or not isinstance(result[1], dict):
        return None
    devices = result[1].get("devices")
    if not isinstance(devices, list):
        return None
    return [d for d in devices if isinstance(d, dict) and all(isinstance(d.get(k), str) for k in ("device_id", "platform", "username", "updated_at"))
            and isinstance(d.get("notifies_watch"), bool)]


def view(devices: list[dict] | None, text) -> dict:
    """`visible` is False without the route; `lines` is one sentence per phone, or the "nothing said yet" sentence."""
    if devices is None:
        return {"visible": False, "lines": ""}
    lines = [f"{d['username']} - {d['platform']} - {text('WATCHNOTICE_ON' if d['notifies_watch'] else 'WATCHNOTICE_OFF')} ({d['updated_at'][:16].replace('T', ' ')} UTC)" for d in devices]
    return {"visible": True, "lines": "\n".join(lines) if lines else text("WATCHNOTICE_NONE")}
