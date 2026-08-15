"""Numerical self-consistency verification of batch 3's new robot
(SO-ARM100 - "quaternion" family, 5 real joints not 6) against real
reference values from HYDRA-UMC-STUDIO's own TypeScript kinematics
(run via `npx tsx`, output captured below, script moved to
SONNET/_papelera/ afterward). Same reasoning as verify_batch1/2's own
headers - both sides authored in the same session, so this checks
TS<->Python agreement.

PiPER and Poppy Ergo Jr were dropped from this batch (mesh format
mismatch - .obj multi-part and .dae respectively, this project's mesh
pipeline only supports .stl) - see SONNET audit log for the full
decision.
"""
import sys
sys.path.insert(0, ".")
import numpy as np
from hydra_suite.render.kinematics import SOARM100, quat_family_link_transforms

POSES = [
    {"j1": 0, "j2": 0, "j3": 0, "j4": 0, "j5": 0, "j6": 0},
    {"j1": 30, "j2": -40, "j3": 25, "j4": 0, "j5": 0, "j6": 0},
    {"j1": -60, "j2": 20, "j3": -30, "j4": 0, "j5": 0, "j6": 0},
]

# Reference values from `npx tsx src/_verify_batch3.mts` in HYDRA-UMC-STUDIO
REF_SOARM100 = [
    (0, 146.63047653894333, 0),
    (58.54021011102077, 146.59472258925643, -27.13007654177862),
    (-89.59888340540061, 96.93004384440907, 71.77199993497871),
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


print("=== SO-ARM100 (x/z + height-offset-consistency check, base_offset excluded, 5-joint chain) ===")
derived = []
for i, pose in enumerate(POSES):
    transforms = quat_family_link_transforms(SOARM100.chain, SOARM100.root_axis_target, (0.0, 0.0, 0.0), pose)
    p = transforms[-1][:3, 3] * 1000
    ref_x, ref_y, ref_z = REF_SOARM100[i]
    check(f"pose{i} p.x", p[0], ref_x)
    check(f"pose{i} p.z", p[2], ref_y)
    derived.append(p[1] - ref_z)
check("height-offset self-consistency (spread)", max(derived) - min(derived), 0.0)

print()
if failures:
    print(f"FAILED: {failures} mismatches")
    sys.exit(1)
else:
    print("ALL BATCH 3 KINEMATICS PORTS SELF-CONSISTENT (TS <-> Python)")
