# =============================================================================
# HYDRA-UMC SUITE - reach.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Where the tool of each model can be, and what a Work asks of it, with no Qt and no network:
#   - the position of the tool of a model from its first three joints, in the frame HYDRA-UMC STUDIO uses for the
#     points of a Work (millimetres, Z up, the origin on the base at the height STUDIO calibrates for the model)
#   - the inverse of that: the joints closest to a position, and how far from it (in millimetres) they leave the tool
#   - a portable Work point (joints of the generic two-link arm, or a Cartesian pose) read as a pose
#   - the largest factor, about the base, at which every point of a Work fits within a tolerance
# The chains are the ones of render/kinematics.py (a handful of wrist offsets that STUDIO uses for its own solver
# are listed in IK_CHAIN_OVERRIDES), the joint ranges are those of joint_limits.py. A model whose forward
# kinematics could not be built has no entry in SUPPORTED_MODELS: its Works are not scaled.
# =============================================================================
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .joint_limits import joint_range_deg
from .render import kinematics as K

DEFAULT_REACH_TOLERANCE_MM = 5.0
MIN_SCALE = 0.1
SCALE_STEP = 0.05

#: Calibrated by STUDIO for these models (the height of the tool at its own home pose, in mm).
_Z_OFFSET_MM = {"Parol6 (6-DOF)": 334.0, "AR3 (6-DOF)": 541.0, "AR4 (6-DOF)": 177.0, "Faze4 (6-DOF)": 597.0}
#: Models whose position in STUDIO is a radius and a height (the base angle is j1 itself).
_CYLINDRICAL = {
    "Parol6 (6-DOF)", "UR3e (6-DOF)", "UR5e (6-DOF)", "UR10e (6-DOF)", "UR16e (6-DOF)", "UR20 (6-DOF)",
    "xArm6 (6-DOF)", "Lite 6 (6-DOF)", "Gen3 Lite (6-DOF)", "Gen2 (6-DOF)", "PiPER (6-DOF)",
}
#: Wrist offset (metres, the y of the fifth step) STUDIO uses in its solver for the classic UR models.
IK_CHAIN_OVERRIDES = {"UR3 (6-DOF)": 0.11235, "UR5 (6-DOF)": 0.10915, "UR10 (6-DOF)": 0.163941}
#: Models whose base joint is aligned to the opposite vertical in STUDIO.
_ROOT_DOWN = {"Koch v1.1 (5-DOF)"}


def generic_cartesian(j1: float, j2: float, j3: float, j4: float = 0.0, j5: float = 0.0, j6: float = 0.0) -> tuple[float, float, float, float, float, float]:
    """The pose of the generic two-link arm (160 mm + 200 mm over a 195 mm column): how a portable Work point that
    holds joints is read."""
    a1, a2, a3 = math.radians(j1), math.radians(j2), math.radians(j3)
    theta = -a2
    radius = 160 * math.sin(theta) + 200 * math.sin(theta + a3)
    height = 160 * math.cos(theta) + 200 * math.cos(theta + a3)
    return radius * math.cos(a1), radius * math.sin(a1), height + 195.0, j4, j5 + j2 - j3 + 180.0, j6


def _spin_batch(axis: tuple[float, float, float], angles: np.ndarray) -> np.ndarray:
    v = np.array(axis, dtype=np.float64)
    x, y, z = v / np.linalg.norm(v)
    c, s = np.cos(angles), np.sin(angles)
    C = 1 - c
    m = np.zeros((angles.shape[0], 4, 4))
    m[:, 0, 0] = x * x * C + c
    m[:, 0, 1] = x * y * C - z * s
    m[:, 0, 2] = x * z * C + y * s
    m[:, 1, 0] = y * x * C + z * s
    m[:, 1, 1] = y * y * C + c
    m[:, 1, 2] = y * z * C - x * s
    m[:, 2, 0] = z * x * C - y * s
    m[:, 2, 1] = z * y * C + x * s
    m[:, 2, 2] = z * z * C + c
    m[:, 3, 3] = 1.0
    return m


@dataclass
class _Rig:
    root: np.ndarray
    fixed: list[np.ndarray]  # translation @ rpy of each of the first three joints
    axes: list[tuple[float, float, float]]
    tail: np.ndarray  # the rest of the chain with every joint at zero (4x4)
    cylindrical: bool
    z_offset_mm: float
    ranges: list[tuple[float, float]]


_RIGS: dict[str, _Rig | None] = {}
_GRIDS: dict[str, tuple[np.ndarray, np.ndarray]] = {}


def _chain_of(model: str) -> tuple[list[K.JointStep], np.ndarray] | None:
    entry = K.ROBOT_REGISTRY.get(model)
    if entry is None or entry.family == "generic":
        return None
    if entry.family == "ur":
        chain, root = list(entry.chain), K.UR_ROOT
        chain = [K.JointStep(s.pos, s.rpy, (0.0, 0.0, 1.0)) for s in chain]
    else:
        cfg = entry.quat_config
        chain = list(cfg.chain)
        c0 = chain[0]
        axis_world = K.rpy_matrix(c0.rpy)[:3, :3] @ np.array(c0.axis, dtype=np.float64)
        target = (0.0, -1.0, 0.0) if model in _ROOT_DOWN else cfg.root_axis_target
        root = K.align_vectors_matrix(axis_world, target)
    wrist = IK_CHAIN_OVERRIDES.get(model)
    if wrist is not None and len(chain) > 4:
        old = chain[4]
        chain[4] = K.JointStep((old.pos[0], wrist, old.pos[2]), old.rpy, old.axis)
    return chain, root


def _build(model: str) -> _Rig | None:
    try:
        built = _chain_of(model)
        if built is None:
            return None
        chain, root = built
        fixed = [K.translation(s.pos) @ K.rpy_matrix(s.rpy) for s in chain[:3]]
        axes = [s.axis for s in chain[:3]]
        tail = np.eye(4)
        for s in chain[3:]:
            tail = tail @ K.translation(s.pos) @ K.rpy_matrix(s.rpy)
        rig = _Rig(root, fixed, axes, tail, model in _CYLINDRICAL, 0.0, [joint_range_deg(model, j) for j in ("j1", "j2", "j3")])
        if model in _Z_OFFSET_MM:
            rig.z_offset_mm = _Z_OFFSET_MM[model]
        else:
            home = K.ROBOT_REGISTRY[model].home_pose_deg
            at = (home.get("j1", 0.0), home.get("j2", 0.0), home.get("j3", 0.0)) if rig.cylindrical else (0.0, 0.0, 0.0)
            rig.z_offset_mm = float(_world_position(rig, np.array([at]))[0][1] * 1000.0)
        return rig
    except Exception:
        return None


def _rig(model: str) -> _Rig | None:
    if model not in _RIGS:
        _RIGS[model] = _build(model)
    return _RIGS[model]


def _world_position(rig: _Rig, joints_deg: np.ndarray) -> np.ndarray:
    n = joints_deg.shape[0]
    t = np.broadcast_to(rig.root, (n, 4, 4)).copy()
    for i in range(3):
        t = t @ rig.fixed[i] @ _spin_batch(rig.axes[i], np.radians(joints_deg[:, i]))
    t = t @ rig.tail
    return t[:, :3, 3]


def _cartesian_batch(rig: _Rig, joints_deg: np.ndarray) -> np.ndarray:
    p = _world_position(rig, joints_deg)
    if rig.cylindrical:
        radius = np.hypot(p[:, 0], p[:, 2]) * 1000.0
        angle = np.radians(joints_deg[:, 0])
        return np.stack([radius * np.cos(angle), radius * np.sin(angle), p[:, 1] * 1000.0 - rig.z_offset_mm], axis=1)
    return np.stack([p[:, 0] * 1000.0, p[:, 2] * 1000.0, p[:, 1] * 1000.0 - rig.z_offset_mm], axis=1)


#: The models whose reach can be worked out here (every model of the registry but the generic one).
def supported_models() -> list[str]:
    return [m for m in K.ROBOT_REGISTRY if _rig(m) is not None]


def is_supported(model: str | None) -> bool:
    return bool(model) and _rig(model) is not None


def forward(model: str, j1: float, j2: float, j3: float) -> tuple[float, float, float]:
    rig = _rig(model)
    if rig is None:
        raise ValueError(f"no kinematics for {model}")
    x, y, z = _cartesian_batch(rig, np.array([[j1, j2, j3]], dtype=np.float64))[0]
    return float(x), float(y), float(z)


def _grid(model: str, rig: _Rig) -> tuple[np.ndarray, np.ndarray]:
    if model not in _GRIDS:
        axes = []
        for lo, hi in rig.ranges:
            count = max(5, min(48, int(round((hi - lo) / 9.0)) + 1))
            axes.append(np.linspace(lo, hi, count))
        mesh = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)
        _GRIDS[model] = (mesh, _cartesian_batch(rig, mesh))
    return _GRIDS[model]


@dataclass(frozen=True)
class Solution:
    joints: tuple[float, float, float]
    residual_mm: float


def inverse(model: str, target: tuple[float, float, float], seed: tuple[float, float, float] | None = None) -> Solution:
    """The joints j1..j3 closest to a position (inside the range of the model) and how far the tool stays from it."""
    rig = _rig(model)
    if rig is None:
        raise ValueError(f"no kinematics for {model}")
    goal = np.array(target, dtype=np.float64)
    lo = np.array([r[0] for r in rig.ranges])
    hi = np.array([r[1] for r in rig.ranges])
    mesh, positions = _grid(model, rig)
    starts: list[np.ndarray] = []
    if seed is not None:
        starts.append(np.clip(np.array(seed, dtype=np.float64), lo, hi))
    distance = np.linalg.norm(positions - goal, axis=1)
    for index in np.argsort(distance)[:5]:
        starts.append(mesh[index].copy())
    best = (math.inf, starts[0])
    for start in starts:
        q = start.copy()
        previous = math.inf
        stalled = 0
        for _ in range(30):
            probes = np.repeat(q[None, :], 4, axis=0)
            for k in range(3):
                probes[k + 1, k] += 0.5
            at = _cartesian_batch(rig, probes)
            p = at[0]
            error = goal - p
            norm = float(np.linalg.norm(error))
            if norm < 1e-3:
                break
            stalled = stalled + 1 if previous - norm < 1e-3 else 0
            if stalled >= 3:
                break
            previous = norm
            jac = ((at[1:] - p) / 0.5).T  # d position / d joint, per degree
            lam = 1e-2 * max(1.0, float(np.linalg.norm(jac)))
            delta = np.linalg.solve(jac.T @ jac + (lam**2) * np.eye(3), jac.T @ error)
            biggest = float(np.max(np.abs(delta)))
            if biggest > 20.0:
                delta *= 20.0 / biggest
            moved = np.clip(q + delta, lo, hi)
            if np.allclose(moved, q, atol=1e-6):
                break
            q = moved
        residual = float(np.linalg.norm(goal - _cartesian_batch(rig, q[None, :])[0]))
        if residual < best[0]:
            best = (residual, q)
        if residual < 1e-2:
            break
    return Solution((float(best[1][0]), float(best[1][1]), float(best[1][2])), float(best[0]))


# --- Works ---------------------------------------------------------------------------------------------------------

@dataclass
class PortablePoint:
    """A point of a Work that is a pose, not joints of the robot: x, y, z in mm and the wrist angles a, b, c."""

    x: float
    y: float
    z: float
    a: float = 0.0
    b: float = 0.0
    c: float = 0.0


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def portable_pose(raw: dict) -> PortablePoint | None:
    """The pose a portable point asks for: its x, y, z when it has them, else the generic arm read from its joints."""
    x, y, z = _number(raw.get("x")), _number(raw.get("y")), _number(raw.get("z"))
    if x is not None and y is not None and z is not None:
        return PortablePoint(x, y, z, _number(raw.get("a")) or 0.0, _number(raw.get("b")) or 0.0, _number(raw.get("c")) or 0.0)
    joints = [_number(raw.get(name)) for name in ("j1", "j2", "j3", "j4", "j5", "j6")]
    if any(v is None for v in joints):
        return None
    px, py, pz, a, b, c = generic_cartesian(*joints)  # type: ignore[arg-type]
    return PortablePoint(px, py, pz, a, b, c)


def solve_pose(model: str, pose: PortablePoint, seed: tuple[float, float, float] | None = None) -> tuple[dict[str, float], float]:
    """All six joints for a pose (the wrist ones follow a, b, c inside their ranges) and the distance, in mm, between
    the pose asked for and the one the joints give."""
    solution = inverse(model, (pose.x, pose.y, pose.z), seed)
    joints = {"j1": solution.joints[0], "j2": solution.joints[1], "j3": solution.joints[2]}
    for name, wanted in (("j4", pose.a), ("j5", pose.b), ("j6", pose.c)):
        lo, hi = joint_range_deg(model, name)
        joints[name] = min(hi, max(lo, wanted))
    return joints, solution.residual_mm


def scaled(pose: PortablePoint, factor: float) -> PortablePoint:
    return PortablePoint(pose.x * factor, pose.y * factor, pose.z * factor, pose.a, pose.b, pose.c)


@dataclass
class ReachScale:
    scale: float
    fits: bool
    remaining: int


def count_over(model: str, poses: list[PortablePoint], tolerance_mm: float, factor: float, limit: int | None = None) -> int:
    """How many poses, scaled by the factor, stay further than the tolerance from what the arm can take (counting
    stops past `limit`, when only a smaller count matters)."""
    over = 0
    seed = None
    for pose in poses:
        joints, residual = solve_pose(model, scaled(pose, factor), seed)
        seed = (joints["j1"], joints["j2"], joints["j3"])
        if not residual <= tolerance_mm:
            over += 1
            if limit is not None and over > limit:
                break
    return over


def _search_scale(model: str, poses: list[PortablePoint], tolerance_mm: float) -> ReachScale:
    """The largest factor (in steps of 5 %, never below 10 %) at which every pose is within the tolerance, scaling
    about the base of the robot; when none fits, the one that leaves the fewest poses over the tolerance."""
    steps = int(math.floor((1 - MIN_SCALE) / SCALE_STEP + 1e-9))
    factors = [round(1 - i * SCALE_STEP, 3) for i in range(steps + 1)]
    first = count_over(model, poses, tolerance_mm, factors[0])
    if first == 0:
        return ReachScale(1.0, True, 0)
    # The factors are tried from the largest down, three steps at a time; once one fits, the two before it are
    # tried so that the largest factor that fits is the one returned. (A point can be too close to the base for the
    # smallest factors, so a smaller factor does not always fit when a larger one does.)
    best = ReachScale(1.0, False, first)
    for index in range(3, len(factors), 3):
        remaining = count_over(model, poses, tolerance_mm, factors[index], best.remaining)
        if remaining == 0:
            for earlier in (index - 2, index - 1):
                if count_over(model, poses, tolerance_mm, factors[earlier], 0) == 0:
                    return ReachScale(factors[earlier], True, 0)
            return ReachScale(factors[index], True, 0)
        if remaining < best.remaining:
            best = ReachScale(factors[index], False, remaining)
    return best


#: Poses used to look for the factor in a long Work (the furthest ones from the base and an even sample of the rest).
_SEARCH_SAMPLE = 40


def find_scale(model: str, poses: list[PortablePoint], tolerance_mm: float = DEFAULT_REACH_TOLERANCE_MM) -> ReachScale:
    """Same as _search_scale, but a long Work is searched with a sample and the factor found is then checked (and
    lowered, if need be) against every pose, so the result is always exact for the whole Work."""
    if len(poses) <= _SEARCH_SAMPLE:
        return _search_scale(model, poses, tolerance_mm)
    by_distance = sorted(range(len(poses)), key=lambda i: -(poses[i].x ** 2 + poses[i].y ** 2 + poses[i].z ** 2))
    chosen = set(by_distance[: _SEARCH_SAMPLE // 2])
    stride = max(1, len(poses) // (_SEARCH_SAMPLE // 2))
    chosen.update(range(0, len(poses), stride))
    found = _search_scale(model, [poses[i] for i in sorted(chosen)], tolerance_mm)
    steps = int(math.floor((1 - MIN_SCALE) / SCALE_STEP + 1e-9))
    factors = [round(1 - i * SCALE_STEP, 3) for i in range(steps + 1)]
    index = min(range(len(factors)), key=lambda i: abs(factors[i] - found.scale))
    while index < len(factors):
        if count_over(model, poses, tolerance_mm, factors[index], 0) == 0:
            return ReachScale(factors[index], True, 0)
        index += 1
    return ReachScale(found.scale, False, count_over(model, poses, tolerance_mm, found.scale))
