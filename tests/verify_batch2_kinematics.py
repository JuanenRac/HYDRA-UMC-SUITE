"""Numerical self-consistency verification of batch 2's new robots
(Gen3 Lite - "ur" family; M-710iC - "quaternion" family) against real
reference values computed directly from HYDRA-UMC-STUDIO's own
TypeScript kinematics files (run via `npx tsx` against a scratch
script, output captured below). Same reasoning as
verify_batch1_kinematics.py's own header - both sides authored in the
same session, no independent third source, so this checks TS<->Python
agreement rather than against pre-existing ground truth.
"""
import sys
sys.path.insert(0, ".")
import numpy as np
from hydra_suite.render.kinematics import (
    GEN3LITE_CHAIN, ur_world_link_transforms,
    M710IC, quat_family_link_transforms,
)

POSES = [
    {"j1": 0, "j2": 0, "j3": 0, "j4": 0, "j5": 0, "j6": 0},
    {"j1": 30, "j2": -40, "j3": 25, "j4": 0, "j5": 0, "j6": 0},
    {"j1": -60, "j2": 20, "j3": -30, "j4": 0, "j5": 0, "j6": 0},
]

# Reference values from `npx tsx src/_verify_batch2.mts` in HYDRA-UMC-STUDIO
REF_GEN3LITE = [
    (57.871013932998984, 0, 0),
    (451.5225880717227, 260.68668776840553, -319.25096290650754),
    (163.69734421202722, -283.53211723932213, -98.24552782126023),
]
REF_M710IC = [
    (1341, 3.5638159090467525e-13, 0),
    (-51.92618561909222, 29.979597245173885, 777.7163443700797),
    (671.6725615801136, 1163.3710027066916, -1025.5524580242504),
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


print("=== Gen3 Lite (radius + height-offset-consistency check) ===")
derived = []
for i, pose in enumerate(POSES):
    transforms = ur_world_link_transforms(GEN3LITE_CHAIN, pose)
    p = transforms[-1][:3, 3] * 1000
    radius = np.hypot(p[0], p[2])
    ref_x, ref_y, ref_z = REF_GEN3LITE[i]
    ref_radius = np.hypot(ref_x, ref_y)
    check(f"pose{i} radius", radius, ref_radius)
    derived.append(p[1] - ref_z)
check("height-offset self-consistency (spread)", max(derived) - min(derived), 0.0)

print("=== M-710iC (x/z + height-offset-consistency check, base_offset excluded) ===")
derived = []
for i, pose in enumerate(POSES):
    transforms = quat_family_link_transforms(M710IC.chain, M710IC.root_axis_target, (0.0, 0.0, 0.0), pose)
    p = transforms[-1][:3, 3] * 1000
    ref_x, ref_y, ref_z = REF_M710IC[i]
    check(f"pose{i} p.x", p[0], ref_x)
    check(f"pose{i} p.z", p[2], ref_y)
    derived.append(p[1] - ref_z)
check("height-offset self-consistency (spread)", max(derived) - min(derived), 0.0)

print()
if failures:
    print(f"FAILED: {failures} mismatches")
    sys.exit(1)
else:
    print("ALL BATCH 2 KINEMATICS PORTS SELF-CONSISTENT (TS <-> Python)")
