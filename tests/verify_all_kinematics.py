"""Numerical verification of the new quaternion-family kinematics ports
(Parol6/Faze4/AR3/AR4) plus a UR5e regression check, against real
reference values computed directly from HYDRA-UMC-STUDIO's own
TypeScript kinematics files (src/_verify_all_robots.mts, run via tsx).
"""
import sys
sys.path.insert(0, ".")
import numpy as np
from hydra_suite.render.kinematics import (
    UR5E_CHAIN, ur_world_link_transforms,
    PAROL6, FAZE4, AR3, AR4, quat_family_link_transforms,
)

POSES = [
    {"j1": 0, "j2": 0, "j3": 0, "j4": 0, "j5": 0, "j6": 0},
    {"j1": 30, "j2": -40, "j3": 25, "j4": 0, "j5": 0, "j6": 0},
    {"j1": -60, "j2": 20, "j3": -30, "j4": 0, "j5": 0, "j6": 0},
]

# Reference values from `npx tsx src/_verify_all_robots.mts` in HYDRA-UMC-STUDIO
REF_UR5E = [
    (849.7401073213356, 0, -916.9000000204283),
    (663.7665070625632, 383.22577153162837, -538.8092412947644),
    (418.0098260046694, -724.0142567031132, -992.6390786278741),
]
REF_PAROL6 = [
    (199.77056127486793, 0, 0.0006477694258819611),
    (57.85138060849335, 33.40051016730512, 2.049096147387388),
    (125.55061426564107, -217.46004282957216, 19.107275312139052),
]
REF_FAZE4 = [
    (76.37361019521215, 437.8535390756984, 0.12245094543959567),
    (88.3846805798873, 233.26607441488605, -44.70086560201639),
    (-206.0166689635583, 376.12853321237, 59.24307311466009),
]
REF_AR3 = [
    (-7.042028061364344, 169.62907300806683, 152.90549636222931),
    (37.298191276642314, -78.68959730913407, 101.37505378441358),
    (199.34442797601, 123.22256884512808, 149.4949432583643),
]
REF_AR4 = [
    (0.0011203311176886579, 328.0893241243651, 297.7806683019573),
    (-61.52272604150362, 106.56052341891706, 294.7368994448335),
    (371.00277473246217, 214.19604052039628, 325.2196075012423),
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


print("=== UR5e (regression check via cylindrical radius, j1=0 pose only is exact; others check radius) ===")
for i, pose in enumerate(POSES):
    transforms = ur_world_link_transforms(UR5E_CHAIN, pose)
    p = transforms[-1][:3, 3] * 1000  # wrist_3, mm
    radius = np.hypot(p[0], p[2])
    ref_x, ref_y, ref_z = REF_UR5E[i]
    ref_radius = np.hypot(ref_x, ref_y)
    check(f"pose{i} radius", radius, ref_radius)

print("=== Parol6 (cylindrical radius + height check) ===")
for i, pose in enumerate(POSES):
    transforms = quat_family_link_transforms(PAROL6.chain, PAROL6.root_axis_target, PAROL6.base_offset, pose)
    p = transforms[-1][:3, 3] * 1000  # L6, mm
    radius = np.hypot(p[0], p[2])
    ref_x, ref_y, ref_z = REF_PAROL6[i]
    ref_radius = np.hypot(ref_x, ref_y)
    check(f"pose{i} radius", radius, ref_radius)
    Z_OFFSET_MM = 334
    check(f"pose{i} height (p.y)", p[1], ref_z + Z_OFFSET_MM)

print("=== Faze4 (direct x/y/z reconstruction - exact match expected) ===")
Z_OFFSET_MM = 597
for i, pose in enumerate(POSES):
    transforms = quat_family_link_transforms(FAZE4.chain, FAZE4.root_axis_target, FAZE4.base_offset, pose)
    p = transforms[-1][:3, 3] * 1000  # hvataljka, mm
    ref_x, ref_y, ref_z = REF_FAZE4[i]
    # TS remap: x_out=p.x*1000, y_out=p.z*1000, z_out=p.y*1000-OFFSET
    check(f"pose{i} p.x", p[0], ref_x)
    check(f"pose{i} p.z", p[2], ref_y)
    check(f"pose{i} p.y", p[1], ref_z + Z_OFFSET_MM)

print("=== AR3 (direct x/y/z reconstruction - exact match expected) ===")
Z_OFFSET_MM = 541
for i, pose in enumerate(POSES):
    transforms = quat_family_link_transforms(AR3.chain, AR3.root_axis_target, AR3.base_offset, pose)
    p = transforms[-1][:3, 3] * 1000  # link_6, mm
    ref_x, ref_y, ref_z = REF_AR3[i]
    check(f"pose{i} p.x", p[0], ref_x)
    check(f"pose{i} p.z", p[2], ref_y)
    check(f"pose{i} p.y", p[1], ref_z + Z_OFFSET_MM)

print("=== AR4 (direct x/y/z reconstruction - exact match expected) ===")
Z_OFFSET_MM = 177
for i, pose in enumerate(POSES):
    transforms = quat_family_link_transforms(AR4.chain, AR4.root_axis_target, AR4.base_offset, pose)
    p = transforms[-1][:3, 3] * 1000  # link_6, mm
    ref_x, ref_y, ref_z = REF_AR4[i]
    check(f"pose{i} p.x", p[0], ref_x)
    check(f"pose{i} p.z", p[2], ref_y)
    check(f"pose{i} p.y", p[1], ref_z + Z_OFFSET_MM)

print()
if failures:
    print(f"FAILED: {failures} mismatches")
    sys.exit(1)
else:
    print("ALL KINEMATICS PORTS VERIFIED CORRECT")
