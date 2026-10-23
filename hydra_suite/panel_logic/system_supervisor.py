# =============================================================================
# HYDRA-UMC SUITE - panel_logic/system_supervisor.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# What the System Supervisor shows, worked out without any window toolkit: the readings of
# GET /api/system/supervisor (polled every two seconds, answering what the host reports right now), a rolling
# window of the last samples so the charts have a line to draw, and the throughput between two samples.
# Every number comes from the server; a field the host cannot supply is shown as "-" or "N/A", never as an
# invented value.
# =============================================================================
from __future__ import annotations

from hydra_suite.i18n import _

#: Two minutes of history at one sample every two seconds.
HISTORY_LEN = 60
POLL_MS = 2000


def format_bytes(n: float | None) -> str:
    if n is None:
        return "-"
    if n < 1024:
        return f"{n:.0f} B"
    units = ["KB", "MB", "GB", "TB"]
    value = n / 1024
    i = 0
    while value >= 1024 and i < len(units) - 1:
        value /= 1024
        i += 1
    return f"{value:.0f} {units[i]}" if value >= 100 else f"{value:.1f} {units[i]}"


def format_uptime(seconds: float) -> str:
    total = int(seconds)
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def network_rate(prev: dict | None, cur: dict | None, dt_sec: float, key: str) -> float | None:
    """The live throughput between two polls: the change in one cumulative byte counter (rxBytes or txBytes)
    divided by the time between them. A counter that went down (the interface was reset between the two samples)
    gives None, never a false negative rate, so "no traffic" and "this pair of samples cannot say" stay apart."""
    if prev is None or cur is None or dt_sec <= 0:
        return None
    delta = cur.get(key, 0) - prev.get(key, 0)
    if delta < 0:
        return None
    return delta / dt_sec


def append_history(history: list[dict], snapshot: dict) -> list[dict]:
    """The window with one more sample, at most HISTORY_LEN long."""
    return [*history[-(HISTORY_LEN - 1):], snapshot]


def _series(history: list[dict], pick) -> list[float | None]:
    out: list[float | None] = []
    for sample in history:
        try:
            value = pick(sample)
        except (KeyError, TypeError, ZeroDivisionError):
            value = None
        out.append(float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None)
    return out


def _percent_of(part: str, total: str):
    def pick(sample: dict):
        memory = sample.get("memory")
        return memory[part] / memory[total] * 100 if memory and memory.get(total) else None

    return pick


def _tile(label_key: str, value: str, sub: str = "") -> dict:
    return {"label": _(label_key), "value": value, "sub": sub}


def build_view(history: list[dict]) -> dict:
    """Everything the screen shows, from the newest sample and the window: the tiles, the per-core bars, the
    chart series (lists of numbers or None for a gap), the network totals and rates, and the process rows."""
    snapshot = history[-1]
    cpu = snapshot.get("cpu") or {}
    memory = snapshot.get("memory")
    disk = snapshot.get("disk")
    temps = snapshot.get("temps") or {}
    network = snapshot.get("network") or {}
    traffic = network.get("traffic") or {}

    overall = cpu.get("overallPercent")
    core_count = cpu.get("coreCount")
    mem_percent = (memory["usedBytes"] / memory["totalBytes"] * 100) if memory and memory.get("totalBytes") else None
    disk_percent = (disk["usedBytes"] / disk["totalBytes"] * 100) if disk and disk.get("totalBytes") else None
    cpu_temp, rp1_temp = temps.get("cpu"), temps.get("rp1")
    load_avg = cpu.get("loadAvg") or []

    tiles = [
        _tile("LBL_SUPERVISOR_CPU", f"{overall:.0f}%" if isinstance(overall, (int, float)) else "-", f"{core_count} {_('LBL_SUPERVISOR_CORES')}" if core_count else ""),
        _tile("LBL_SUPERVISOR_MEMORY", f"{mem_percent:.0f}%" if mem_percent is not None else "N/A", f"{format_bytes(memory['usedBytes'])} / {format_bytes(memory['totalBytes'])}" if memory else ""),
        _tile("LBL_SUPERVISOR_DISK", f"{disk_percent:.0f}%" if disk_percent is not None else "N/A", f"{format_bytes(disk['usedBytes'])} / {format_bytes(disk['totalBytes'])}" if disk else ""),
        _tile("LBL_SUPERVISOR_CPU_TEMP", f"{cpu_temp:.0f}°C" if isinstance(cpu_temp, (int, float)) else "N/A"),
        _tile("LBL_SUPERVISOR_RP1_TEMP", f"{rp1_temp:.0f}°C" if isinstance(rp1_temp, (int, float)) else "N/A"),
        _tile("LBL_SUPERVISOR_LOAD_AVG", f"{load_avg[0]:.2f}" if load_avg else "-", f"{load_avg[1]:.2f} / {load_avg[2]:.2f}" if len(load_avg) >= 3 else ""),
    ]

    per_core = cpu.get("perCorePercent") or []
    per_freq = cpu.get("perCoreFrequencyMHz") or []
    cores = [
        {
            "name": f"C{i}",
            "percent": max(0, min(100, round(pct))),
            "frequency": f"{per_freq[i]} MHz" if i < len(per_freq) and per_freq[i] is not None else "",
        }
        for i, pct in enumerate(per_core)
    ]

    def net_total(entry: dict | None) -> dict | None:
        if entry is None:
            return None
        return {"total": format_bytes(entry["rxBytes"] + entry["txBytes"]), "sub": f"↓ {format_bytes(entry['rxBytes'])} · ↑ {format_bytes(entry['txBytes'])}"}

    rates: dict[str, list[float | None]] = {"wifiRx": [], "wifiTx": [], "ethRx": [], "ethTx": []}
    for i in range(1, len(history)):
        prev, cur = history[i - 1], history[i]
        dt = (cur.get("timestamp", 0) - prev.get("timestamp", 0)) / 1000
        prev_t = ((prev.get("network") or {}).get("traffic")) or {}
        cur_t = ((cur.get("network") or {}).get("traffic")) or {}
        rates["wifiRx"].append(network_rate(prev_t.get("wifi"), cur_t.get("wifi"), dt, "rxBytes"))
        rates["wifiTx"].append(network_rate(prev_t.get("wifi"), cur_t.get("wifi"), dt, "txBytes"))
        rates["ethRx"].append(network_rate(prev_t.get("ethernet"), cur_t.get("ethernet"), dt, "rxBytes"))
        rates["ethTx"].append(network_rate(prev_t.get("ethernet"), cur_t.get("ethernet"), dt, "txBytes"))

    processes = [
        {
            "pid": str(p.get("pid", "-")),
            "name": str(p.get("name", "?")),
            "cpu": f"{p.get('cpuPercent', 0):.1f}",
            "mem": f"{p.get('memPercent', 0):.1f}",
            "rss": format_bytes(p.get("rssBytes")),
        }
        for p in (snapshot.get("processes") or [])
        if isinstance(p, dict)
    ]

    def state(value: object) -> str:
        return "on" if value is True else ("off" if value is False else "unknown")

    return {
        "uptime": f"{_('LBL_SUPERVISOR_UPTIME')}: {format_uptime(snapshot.get('uptimeSeconds', 0))}",
        "wifi": state(network.get("wifi")),
        "bluetooth": state(network.get("bluetooth")),
        "ethernet": state(network.get("ethernet")),
        "tiles": tiles,
        "cores": cores,
        "cpuSeries": _series(history, lambda s: (s.get("cpu") or {}).get("overallPercent") or 0),
        "memUsedSeries": _series(history, _percent_of("usedBytes", "totalBytes")),
        "memCachedSeries": _series(
            history,
            lambda s: ((s["memory"]["cachedBytes"] + s["memory"]["buffersBytes"]) / s["memory"]["totalBytes"] * 100) if s.get("memory") and s["memory"].get("totalBytes") else None,
        ),
        "cpuTempSeries": _series(history, lambda s: (s.get("temps") or {}).get("cpu")),
        "rp1TempSeries": _series(history, lambda s: (s.get("temps") or {}).get("rp1")),
        "hasMemory": any(s.get("memory") for s in history),
        "hasTemps": any(isinstance((s.get("temps") or {}).get(k), (int, float)) for s in history for k in ("cpu", "rp1")),
        "hasTraffic": bool(traffic.get("wifi") or traffic.get("ethernet")),
        "wifiTotal": net_total(traffic.get("wifi")),
        "ethernetTotal": net_total(traffic.get("ethernet")),
        "rates": rates,
        "processes": processes,
    }
