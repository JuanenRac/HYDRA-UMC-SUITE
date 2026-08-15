"""Numerical self-consistency verification of batch 4's new robots
(Gen2, PiPER - "ur" family; Z1, ViperX 300, WidowX 250 - "quaternion"
family) against real reference values from HYDRA-UMC-STUDIO's own
TypeScript kinematics (run via `npx tsx`, output captured below, script
moved to SONNET/_papelera/ afterward). Same reasoning as
verify_batch1/2/3's own headers.

ViperX 300 / WidowX 250 are also the first "quat family" robots with a
real per-link mesh offset (see kinematics.py's own
quat_family_mesh_world_transforms() header) - their own check below
verifies the FK POSITION only (mesh_offsets don't affect where the joint
chain itself ends up, only where each link's own mesh is drawn on top of
it), same as every other robot here.
"""
import sys
sys.path.insert(0, ".")
import numpy as np
from hydra_suite.render.kinematics import (
    GEN2_CHAIN, PIPER_CHAIN, ur_world_link_transforms,
    Z1, VX300S, WX250S, quat_family_link_transforms,
)

POSES = [
    {"j1": 0, "j2": 0, "j3": 0, "j4": 0, "j5": 0, "j6": 0},
    {"j1": 30, "j2": -40, "j3": 25, "j4": 0, "j5": 0, "j6": 0},
    {"j1": -60, "j2": 20, "j3": -30, "j4": 0, "j5": 0, "j6": 0},
]

# Reference values from `npx tsx src/_verify_batch4.mts` in HYDRA-UMC-STUDIO
REF_GEN2 = [
    (9.799999998499445, 0, 0),
    (66.07541147882128, 38.148656604112745, -23.769456019920945),
    (10.499847642587206, -18.18626958869334, -49.32410303420183),
]
REF_PIPER = [
    (56.1424716349778, 0, 0),
    (62.79131424762706, 36.252582183637855, -104.69470192433766),
    (36.14077949817908, -62.597666315989784, 152.26236338016088),
]
REF_Z1 = [
    (-12.79999999999997, 3.5638159090467525e-14, 0),
    (37.10221528286567, -21.4209739810939, -139.64410928324182),
    (-3.3565945431831867, -5.813792289201654, 177.39525759496874),
]
REF_VX300S = [
    (429.29400000000004, 9.482414853323462e-14, 0),
    (181.80206505476656, -104.96347119859918, 63.78812410491321),
    (261.3457481976237, 452.66411422038647, 25.7458585040103),
]
REF_WX250S = [
    (364.75, 8.008038676621255e-14, 0),
    (157.33987979220933, -90.8402219522953, 55.01779356894389),
    (221.23459295718087, 383.1895553936569, 22.606829031108077),
]

TOL_MM = 0.01
failures = 0


def check(name, actual, expected, tol=TOL_MM):
    global failures
    err = abs(actual - expected)
    status = "OK" if err < tol else "FAIL"
    if status == "FAIL":
        failures += 1
    print(f"  [{status}] {name}: got {actual:.6f}, expected {expected:.6f}, err {err:.6f}mm")


def check_ur_family(name, chain, ref):
    print(f"=== {name} (radius + height-offset-consistency check) ===")
    derived = []
    for i, pose in enumerate(POSES):
        transforms = ur_world_link_transforms(chain, pose)
        p = transforms[-1][:3, 3] * 1000
        radius = np.hypot(p[0], p[2])
        ref_x, ref_y, ref_z = ref[i]
        ref_radius = np.hypot(ref_x, ref_y)
        check(f"pose{i} radius", radius, ref_radius)
        derived.append(p[1] - ref_z)
    check("height-offset self-consistency (spread)", max(derived) - min(derived), 0.0)


def check_quat_family(name, cfg, ref):
    print(f"=== {name} (x/z + height-offset-consistency check, base_offset excluded, mesh_offsets excluded) ===")
    derived = []
    for i, pose in enumerate(POSES):
        # FK position only - mesh_offsets deliberately excluded (see module docstring).
        transforms = quat_family_link_transforms(cfg.chain, cfg.root_axis_target, (0.0, 0.0, 0.0), pose)
        p = transforms[-1][:3, 3] * 1000
        ref_x, ref_y, ref_z = ref[i]
        check(f"pose{i} p.x", p[0], ref_x)
        check(f"pose{i} p.z", p[2], ref_y)
        derived.append(p[1] - ref_z)
    check("height-offset self-consistency (spread)", max(derived) - min(derived), 0.0)


check_ur_family("Gen2", GEN2_CHAIN, REF_GEN2)
check_ur_family("PiPER", PIPER_CHAIN, REF_PIPER)
check_quat_family("Z1", Z1, REF_Z1)
check_quat_family("ViperX 300", VX300S, REF_VX300S)
check_quat_family("WidowX 250", WX250S, REF_WX250S)

print()
if failures:
    print(f"FAILED: {failures} mismatches")
    sys.exit(1)
else:
    print("ALL BATCH 4 KINEMATICS PORTS SELF-CONSISTENT (TS <-> Python)")
