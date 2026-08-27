"""Numerical verification of batch 1's new robots (xArm6, Lite6 - "ur"
family; e.DO - "quaternion" family) against real reference values computed
directly from HYDRA-UMC-STUDIO's own TypeScript kinematics files (run via
`npx tsx` against a scratch script, output captured below, script moved to
SONNET/_papelera/ per project convention afterward).

Unlike verify_all_kinematics.py's robots (which pre-existed in STUDIO and
so had independent ground truth to check the Python port against), these
3 robots were authored in TS and Python in the SAME session with no third
independent source - so this is a cross-language SELF-CONSISTENCY check
(same real URDF chain data, same math, two independent implementations)
rather than a check against pre-existing, separately-verified TS code.
Transcription correctness against the real URDF source files themselves
was checked by direct comparison when the data was extracted (see
kinematics.py's own header comments for each robot).
"""
import sys
sys.path.insert(0, ".")
import numpy as np
from hydra_suite.render.kinematics import (
    XARM6_CHAIN, LITE6_CHAIN, ur_world_link_transforms,
    EDO, quat_family_link_transforms,
)

POSES = [
    {"j1": 0, "j2": 0, "j3": 0, "j4": 0, "j5": 0, "j6": 0},
    {"j1": 30, "j2": -40, "j3": 25, "j4": 0, "j5": 0, "j6": 0},
    {"j1": -60, "j2": 20, "j3": -30, "j4": 0, "j5": 0, "j6": 0},
]

# Reference values from `npx tsx src/_verify_batch1.mts` in HYDRA-UMC-STUDIO
REF_XARM6 = [
    (207.000000000783, 0, 0),
    (104.0364002761937, 60.065443704980076, 22.533103954618454),
    (187.5323250803164, -324.8155151006312, -2.1235392313098203),
]
REF_LITE6 = [
    (86.99860412231804, 0, 0),
    (148.09978656169625, 85.50545163832143, 199.51400119419947),
    (48.921683598781804, -84.7348415848991, 24.91309212205951),
]
REF_EDO = [
    (69.88794089099017, 0.003746727778917659, 0),
    (-52.49555188051345, -221.3571115574197, -59.95250169266819),
    (60.66308608445313, 6.678834570729923, -21.234864550124257),
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
    derived_offsets = []
    for i, pose in enumerate(POSES):
        transforms = ur_world_link_transforms(chain, pose)
        p = transforms[-1][:3, 3] * 1000
        radius = np.hypot(p[0], p[2])
        ref_x, ref_y, ref_z = ref[i]
        ref_radius = np.hypot(ref_x, ref_y)
        check(f"pose{i} radius", radius, ref_radius)
        derived_offsets.append(p[1] - ref_z)
    # every pose must derive the SAME offset (p.y_python*1000 - z_ts) -
    # if it doesn't, the height doesn't just differ by a constant, meaning
    # the chains have genuinely diverged, not just a home-pose Z reference choice.
    spread = max(derived_offsets) - min(derived_offsets)
    check(f"height-offset self-consistency (spread across poses)", spread, 0.0)


def check_quat_family(name, cfg, ref):
    print(f"=== {name} (x/z radius + height-offset-consistency check, base_offset excluded) ===")
    derived_offsets = []
    for i, pose in enumerate(POSES):
        transforms = quat_family_link_transforms(cfg.chain, cfg.root_axis_target, (0.0, 0.0, 0.0), pose)
        p = transforms[-1][:3, 3] * 1000
        ref_x, ref_y, ref_z = ref[i]
        # TS remap: x_out=p.x*1000, y_out=p.z*1000, z_out=p.y*1000-OFFSET
        check(f"pose{i} p.x", p[0], ref_x)
        check(f"pose{i} p.z", p[2], ref_y)
        derived_offsets.append(p[1] - ref_z)
    spread = max(derived_offsets) - min(derived_offsets)
    check(f"height-offset self-consistency (spread across poses)", spread, 0.0)


check_ur_family("xArm6", XARM6_CHAIN, REF_XARM6)
check_ur_family("Lite6", LITE6_CHAIN, REF_LITE6)
check_quat_family("e.DO", EDO, REF_EDO)

print()
if failures:
    print(f"FAILED: {failures} mismatches")
    sys.exit(1)
else:
    print("ALL BATCH 1 KINEMATICS PORTS SELF-CONSISTENT (TS <-> Python)")
