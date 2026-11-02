# =============================================================================
# HYDRA-UMC SUITE - trajectory_view.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The path of a trajectory drawn from three sides and checked before it is played, with no Qt and no network. The same
# rules as HYDRA-UMC-STUDIO's check before Play: a joint outside the range of its model, a step that swings a joint
# a long way. The position of a point comes from its own x, y, z when it has them, else from the kinematics of the
# model (hydra_suite/reach.py: the first three joints, the same function the import of a Work uses). The numbers
# (largest step, tolerance, lines listed, size of the views) are in assets/trajectory_view.json; whether Play shows
# the check first is a switch of the operator, off until switched on.
# =============================================================================
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable

from hydra_suite import reach
from hydra_suite.joint_limits import joint_range_deg

CONFIG_PATH = Path(__file__).resolve().parent.parent / "assets" / "trajectory_view.json"
JOINTS = ("j1", "j2", "j3", "j4", "j5", "j6")
PLANES = ("top", "side", "front")

_FALLBACK: dict[str, Any] = {
    "previewBeforePlayByDefault": False,
    "maxJointStepDeg": 90,
    "jointLimitToleranceDeg": 0.5,
    "listedIssues": 12,
    "view": {"width": 220, "height": 170, "padding": 12},
}


def load_settings(path: Path = CONFIG_PATH) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return json.loads(json.dumps(_FALLBACK))
    merged = json.loads(json.dumps(_FALLBACK))
    if isinstance(data, dict):
        for key in ("maxJointStepDeg", "jointLimitToleranceDeg"):
            value = data.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
                merged[key] = float(value)
        if isinstance(data.get("listedIssues"), int) and data["listedIssues"] > 0:
            merged["listedIssues"] = data["listedIssues"]
        if isinstance(data.get("previewBeforePlayByDefault"), bool):
            merged["previewBeforePlayByDefault"] = data["previewBeforePlayByDefault"]
        view = data.get("view")
        if isinstance(view, dict) and all(isinstance(view.get(k), (int, float)) and view[k] > 0 for k in ("width", "height", "padding")):
            merged["view"] = {k: float(view[k]) for k in ("width", "height", "padding")}
    return merged


SETTINGS = load_settings()
MAX_STEP_DEG: float = SETTINGS["maxJointStepDeg"]
LIMIT_TOLERANCE_DEG: float = SETTINGS["jointLimitToleranceDeg"]
LISTED_ISSUES: int = SETTINGS["listedIssues"]
VIEW: dict[str, float] = SETTINGS["view"]


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def position_of(model: str | None, point: dict[str, Any]) -> tuple[float, float, float] | None:
    """x, y, z in millimetres: the point's own when it has all three, else from its first three joints."""
    if _finite(point.get("x")) and _finite(point.get("y")) and _finite(point.get("z")):
        return float(point["x"]), float(point["y"]), float(point["z"])
    if all(_finite(point.get(j)) for j in JOINTS[:3]) and model and reach.is_supported(model):
        return reach.forward(model, float(point["j1"]), float(point["j2"]), float(point["j3"]))
    return None


def analyze(points: Iterable[dict[str, Any]], model: str | None, max_step_deg: float | None = None, limit_tolerance_deg: float | None = None) -> dict[str, Any]:
    """The report of a trajectory: path (mm), its length, the largest swing of a joint, and the issues found."""
    step_limit = MAX_STEP_DEG if max_step_deg is None else max_step_deg
    tolerance = LIMIT_TOLERANCE_DEG if limit_tolerance_deg is None else limit_tolerance_deg
    rows = list(points)
    issues: list[dict[str, Any]] = []
    path: list[tuple[float, float, float]] = []
    largest = 0.0
    for index, point in enumerate(rows):
        for joint in JOINTS:
            value = point.get(joint)
            if not _finite(value):
                continue
            low, high = joint_range_deg(model, joint)
            if value < low - tolerance or value > high + tolerance:
                issues.append({"kind": "limit", "point": index, "joint": joint, "value": float(value), "min": low, "max": high})
        position = position_of(model, point)
        if position is not None:
            path.append(position)
        if index > 0:
            worst: tuple[str, float] | None = None
            for joint in JOINTS:
                before, now = rows[index - 1].get(joint), point.get(joint)
                if _finite(before) and _finite(now):
                    delta = abs(float(now) - float(before))
                    if worst is None or delta > worst[1]:
                        worst = (joint, delta)
            if worst is not None:
                largest = max(largest, worst[1])
                if worst[1] > step_limit:
                    issues.append({"kind": "step", "point": index, "joint": worst[0], "delta": worst[1]})
    length = sum(math.dist(path[i - 1], path[i]) for i in range(1, len(path)))
    return {"points": len(rows), "lengthMm": length, "maxStepDeg": largest, "issues": issues, "clean": not issues, "path": path}


def project(path: list[tuple[float, float, float]], plane: str, width: float | None = None, height: float | None = None, padding: float | None = None) -> list[tuple[float, float]]:
    """The path on one plane ("top" x-y, "side" y-z, "front" x-z) fitted in a view of width x height, vertical axis upwards."""
    w = VIEW["width"] if width is None else width
    h = VIEW["height"] if height is None else height
    pad = VIEW["padding"] if padding is None else padding
    if not path:
        return []
    pick = {"top": lambda p: (p[0], p[1]), "side": lambda p: (p[1], p[2]), "front": lambda p: (p[0], p[2])}.get(plane)
    if pick is None:
        raise ValueError(f"unknown plane {plane!r}")
    flat = [pick(p) for p in path]
    us, vs = [p[0] for p in flat], [p[1] for p in flat]
    span = max(max(us) - min(us), max(vs) - min(vs), 1e-6)
    scale = min((w - 2 * pad) / span, (h - 2 * pad) / span)
    offset_u = (w - (max(us) - min(us)) * scale) / 2
    offset_v = (h - (max(vs) - min(vs)) * scale) / 2
    return [(offset_u + (u - min(us)) * scale, h - (offset_v + (v - min(vs)) * scale)) for u, v in flat]


def issue_key(issue: dict[str, Any]) -> str:
    """The language key of the sentence of an issue."""
    return "TRJ_ISSUE_LIMIT" if issue["kind"] == "limit" else "TRJ_ISSUE_STEP"
