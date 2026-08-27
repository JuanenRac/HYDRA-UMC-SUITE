"""Numerical self-consistency verification of batch 5's new robot
(Koch v1.1 / Low-Cost Robot Arm - "quaternion" family, 5 real joints not
6) against real reference values from HYDRA-UMC-STUDIO's own TypeScript
kinematics (run via `npx tsx`, output captured below, script moved to
SONNET/_papelera/ afterward). Same reasoning as verify_batch1-4's own
headers.

FR3 (Franka) was dropped from this batch - a real 7-DOF robot doesn't
fit this app's own j1..j6 joint model, and the user chose to defer it
rather than extend the joint count. Poppy Ergo Jr remains deferred from
batch 3 (no STL source found).
"""
import sys
sys.path.insert(0, ".")
import numpy as np
from hydra_suite.render.kinematics import KOCH, quat_family_link_transforms

POSES = [
    {"j1": 0, "j2": 0, "j3": 0, "j4": 0, "j5": 0, "j6": 0},
    {"j1": 30, "j2": -40, "j3": 25, "j4": 0, "j5": 0, "j6": 0},
    {"j1": -60, "j2": 20, "j3": -30, "j4": 0, "j5": 0, "j6": 0},
]

# Reference values from `npx tsx src/_verify_batch5.mts` in HYDRA-UMC-STUDIO
REF_KOCH = [
    (-148.28, -1.2529999999999608, 0),
    (-114.09695418617919, 71.35527066879321, 168.25917324679358),
    (-21.07045383439929, -59.78570627054047, -109.01031680467537),
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


print("=== Koch v1.1 (x/z + height-offset-consistency check, base_offset excluded, 5-joint chain) ===")
derived = []
for i, pose in enumerate(POSES):
    transforms = quat_family_link_transforms(KOCH.chain, KOCH.root_axis_target, (0.0, 0.0, 0.0), pose)
    p = transforms[-1][:3, 3] * 1000
    ref_x, ref_y, ref_z = REF_KOCH[i]
    check(f"pose{i} p.x", p[0], ref_x)
    check(f"pose{i} p.z", p[2], ref_y)
    derived.append(p[1] - ref_z)
check("height-offset self-consistency (spread)", max(derived) - min(derived), 0.0)

print()
if failures:
    print(f"FAILED: {failures} mismatches")
    sys.exit(1)
else:
    print("ALL BATCH 5 KINEMATICS PORTS SELF-CONSISTENT (TS <-> Python)")
