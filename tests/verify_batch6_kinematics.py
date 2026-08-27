"""Numerical self-consistency verification of batch 6's new robots
(UR3/UR5/UR10 classic, pre-e-Series - "quaternion" family despite being
Universal Robots products, since this generation mixes Y/Z joint axes
unlike the e-Series' own shared-Z engine) against real reference values
from HYDRA-UMC-STUDIO's own TypeScript kinematics (run via `npx tsx`,
output captured below).
Same reasoning as verify_batch1-5's own headers.
"""
import sys
sys.path.insert(0, ".")
import numpy as np
from hydra_suite.render.kinematics import UR3CLASSIC, UR5CLASSIC, UR10CLASSIC, quat_family_link_transforms

POSES = [
    {"j1": 0, "j2": 0, "j3": 0, "j4": 0, "j5": 0, "j6": 0},
    {"j1": 30, "j2": -40, "j3": 25, "j4": 0, "j5": 0, "j6": 0},
    {"j1": -60, "j2": 20, "j3": -30, "j4": 0, "j5": 0, "j6": 0},
]

# Reference values from `npx tsx src/_verify_batch6.mts` in HYDRA-UMC-STUDIO
REF_UR3CLASSIC = [
    (456.90000000000003, -112.34999999999997, 0),
    (302.98358938083527, -304.65826237597304, 214.71659319446582),
    (324.19157028928794, 336.81627112658344, -45.00607575341835),
]
REF_UR5CLASSIC = [
    (817.25, -109.14999999999998, 0),
    (576.7146652231306, -459.0019309762745, 377.93162509998274),
    (495.57467530768383, 640.0605165773575, -75.80711704616138),
]
REF_UR10CLASSIC = [
    (1184.3, -163.94099999999995, 0),
    (828.7105624409988, -667.7590272680294, 545.4505385386893),
    (721.3712982847879, 921.5697397511759, -108.17973266003773),
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


def check_robot(name, cfg, ref):
    print(f"=== {name} (x/z + height-offset-consistency check, base_offset excluded) ===")
    derived = []
    for i, pose in enumerate(POSES):
        transforms = quat_family_link_transforms(cfg.chain, cfg.root_axis_target, (0.0, 0.0, 0.0), pose)
        p = transforms[-1][:3, 3] * 1000
        ref_x, ref_y, ref_z = ref[i]
        check(f"pose{i} p.x", p[0], ref_x)
        check(f"pose{i} p.z", p[2], ref_y)
        derived.append(p[1] - ref_z)
    check("height-offset self-consistency (spread)", max(derived) - min(derived), 0.0)


check_robot("UR3 classic", UR3CLASSIC, REF_UR3CLASSIC)
check_robot("UR5 classic", UR5CLASSIC, REF_UR5CLASSIC)
check_robot("UR10 classic", UR10CLASSIC, REF_UR10CLASSIC)

print()
if failures:
    print(f"FAILED: {failures} mismatches")
    sys.exit(1)
else:
    print("ALL BATCH 6 KINEMATICS PORTS SELF-CONSISTENT (TS <-> Python)")
