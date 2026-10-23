# =============================================================================
# HYDRA-UMC SUITE - panel_logic/ecosystem_telemetry.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The values and helpers of the ecosystem telemetry panel that do not depend on any window toolkit: the Qt Quick
# interface and the checks use them directly.
# =============================================================================
from __future__ import annotations

_AGGREGATES = ["avg", "min", "max", "sum"]


_RANGE_PRESETS = [("5m", 5 * 60 * 1000), ("1h", 60 * 60 * 1000), ("6h", 6 * 60 * 60 * 1000), ("24h", 24 * 60 * 60 * 1000)]


def _number(value) -> float | None:
    """A finite number, or None for null, text, booleans, NaN and infinity."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if number == number and number not in (float("inf"), float("-inf")) else None


def clean_points(points, time_key: str) -> list[tuple[float, float]]:
    """(time, value) pairs of the entries that carry both as numbers; a null
    value, a missing time or an entry that is not an object is left out."""
    pairs = []
    for point in points if isinstance(points, list) else []:
        if not isinstance(point, dict):
            continue
        when, value = _number(point.get(time_key)), _number(point.get("value"))
        if when is not None and value is not None:
            pairs.append((when, value))
    return pairs


QUERY_POINT_LIMIT = 1000  # what the data service returns at most for one query


def telemetry_notices(is_aggregate: bool, params: dict, count: int) -> list[tuple[str, dict]]:
    """Language keys (with their values) for what the operator should know about
    a result: series mixed in one line, and a result cut at the service limit."""
    notices = []
    if count and not is_aggregate and not any(params.get(k) for k in ("sourceId", "kind", "field")):
        notices.append(("MSG_TELEMETRY_MIXED_SERIES", {}))
    if count >= QUERY_POINT_LIMIT:
        notices.append(("MSG_TELEMETRY_LIMIT_REACHED", {"count": count}))
    return notices
