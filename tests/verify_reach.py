# =============================================================================
# HYDRA-UMC SUITE - tests/verify_reach.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# hydra_suite/reach.py, with no Qt and no network:
#   - the position of the tool of every model from its first three joints equals the one HYDRA-UMC STUDIO gives
#     (reference values taken from its own kinematics)
#   - the inverse finds the joints of a pose the arm can take, inside the range of the model
#   - a portable Work point is read as a pose (joints of the generic arm, or x, y, z)
#   - the Work is scaled about the base to the largest factor that fits, or says that none does
# =============================================================================
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hydra_suite import reach
from hydra_suite.joint_limits import joint_range_deg
from hydra_suite.render.kinematics import ROBOT_REGISTRY

failures = 0


def check(label, ok, detail=""):
    global failures
    if not ok:
        print(f"FAIL {label} {detail}")
        failures += 1
    else:
        print(f"ok   {label}")


#: model -> [j1, j2, j3, x, y, z] taken from the kinematics of STUDIO (millimetres, degrees)
STUDIO_REFERENCE = {
    "Parol6 (6-DOF)": [[77.7882, -21.5688, 4.9937, 24.085, 111.285, 35.897], [168.8986, 20.9349, 12.6774, -253.841, 49.808, -116.777]],
    "Faze4 (6-DOF)": [[38.5266, 67.7922, -162.9259, 199.772, 367.386, 140.661], [18.3854, -17.4482, 3.6943, 113.817, 325.196, 33.665]],
    "AR3 (6-DOF)": [[-129.6283, 14.6759, 159.6544, 49.263, -31.649, -305.151], [68.2023, 6.1616, 110.8764, -229.481, 84.19, -261.914]],
    "AR4 (6-DOF)": [[161.7467, -37.7591, -30.4049, 7.655, 23.211, 478.914], [-41.4389, -19.358, 37.6285, 141.422, 160.191, 197.791]],
    "UR3e (6-DOF)": [[93.7101, -26.1503, -155.1584, -14.441, 222.71, -268.952], [167.0523, 100.7137, 101.8197, -298.294, 68.58, -535.518]],
    "UR5e (6-DOF)": [[30.7851, 23.2971, 54.5849, 379.385, 226.025, -1389.677], [-143.0642, -75.7277, -81.2048, -254.442, -191.289, -159.919]],
    "UR10e (6-DOF)": [[157.3672, -4.5005, -37.8856, -1062.43, 442.961, -839.402], [-23.6146, 109.4218, 19.8565, 659.409, -288.289, -2128.635]],
    "UR16e (6-DOF)": [[-146.0839, -123.6645, -58.8328, -575.836, -387.181, -336.179], [162.0554, 28.5253, 131.0597, -279.313, 90.456, -1080.11]],
    "UR20 (6-DOF)": [[-58.1468, -129.7631, 60.0382, 203.411, -327.389, -299.737], [111.508, -0.1088, 72.9116, -363.383, 922.124, -2332.283]],
    "xArm6 (6-DOF)": [[148.5407, 64.2293, -28.6458, -126.724, 77.533, -216.238], [-60.8737, -36.4248, -99.7446, 32.979, -59.187, 839.04]],
    "Lite 6 (6-DOF)": [[0.0841, 54.7784, 90.9343, 404.953, 0.594, 22.461], [-110.2894, -73.8833, 99.088, -84.324, -228.087, 444.062]],
    "e.DO (6-DOF)": [[61.4781, -85.4831, -146.3249, 174.716, 43.434, -880.02], [80.1895, -111.4637, -67.5288, -143.171, -53.531, -1137.167]],
    "Gen3 Lite (6-DOF)": [[-142.3614, 70.8931, -115.9232, -221.576, -170.875, -892.638], [79.5094, 37.321, 129.1141, 32.512, 175.582, -475.253]],
    "M-710iC (6-DOF)": [[155.3901, 43.0627, -146.7279, 416.877, 190.949, -369.37], [105.8185, 149.1954, -136.827, -207.407, -732.058, -595.603]],
    "SO-ARM100 (5-DOF)": [[97.8695, -19.9815, 30.6863, 106.465, 30.485, -74.709], [93.8909, -82.0993, -71.9626, -161.461, 56.182, -64.226]],
    "Gen2 (6-DOF)": [[-71.5075, 83.391, -19.1338, 65.067, -194.551, 110.556], [12.956, 128.9245, 3.4772, 146.583, 33.723, 340.077]],
    "PiPER (6-DOF)": [[-125.9927, 20.5992, -98.475, -135.215, -186.157, 387.137], [80.2778, 21.6739, -55.8629, 0.487, 2.842, 282.891]],
    "Z1 (6-DOF)": [[113.1526, -114.8783, -106.0853, 27.53, 64.379, -638.625], [17.4957, 138.6408, 91.959, 4.412, -1.391, 398.657]],
    "ViperX 300 (6-DOF)": [[113.5642, -22.746, -104.6666, 114.221, 261.889, 293.374], [-117.1473, 147.4571, 119.1931, -40.871, 79.706, -215.818]],
    "WidowX 250 (6-DOF)": [[-4.8446, -169.4503, 77.1253, -107.076, -9.075, -171.925], [-88.7661, 96.1544, -157.1865, 8.523, 395.694, -50.675]],
    "Koch v1.1 (5-DOF)": [[-13.5265, -146.1834, 62.0313, 91.527, -17.843, -142.814], [50.6863, 35.0226, -50.76, 37.657, 33.31, 131.468]],
    "UR3 (6-DOF)": [[-22.2512, -132.2303, -114.9395, -248.07, -252.38, 102.333], [-125.5272, -37.5711, 124.3515, 43.993, 178.71, 16.208]],
    "UR5 (6-DOF)": [[90.6305, -165.6746, 109.2664, -124.017, 117.292, 474.184], [166.3148, -26.6112, 89.6941, -489.366, 9.801, -107.581]],
    "UR10 (6-DOF)": [[-56.1519, -167.0326, -124.4148, -98.726, -529.587, -321.944], [37.6748, 76.8956, -53.2545, 357.887, -545.444, -815.849]]}


def forward_matches_studio():
    check("every model of the registry but the generic one has kinematics", sorted(reach.supported_models()) == sorted(m for m in ROBOT_REGISTRY if m != "Generic (6-DOF)"))
    for model, rows in STUDIO_REFERENCE.items():
        worst = max(math.dist(reach.forward(model, r[0], r[1], r[2]), r[3:]) for r in rows)
        check(f"forward: {model} matches STUDIO", worst < 0.05, f"(off by {worst:.3f} mm)")


def inverse_finds_poses():
    rng = random.Random(7)
    for model in reach.supported_models():
        worst = 0.0
        outside = False
        for _ in range(6):
            joints = []
            for name in ("j1", "j2", "j3"):
                lo, hi = joint_range_deg(model, name)
                joints.append(rng.uniform(max(lo, -150), min(hi, 150)))
            target = reach.forward(model, *joints)
            solution = reach.inverse(model, target)
            worst = max(worst, solution.residual_mm)
            for value, name in zip(solution.joints, ("j1", "j2", "j3")):
                lo, hi = joint_range_deg(model, name)
                outside = outside or not (lo - 1e-6 <= value <= hi + 1e-6)
        check(f"inverse: {model} finds a pose it can take", worst < 0.5 and not outside, f"(worst {worst:.3f} mm, outside range: {outside})")


def portable_points():
    pose = reach.portable_pose({"j1": 0, "j2": -45, "j3": 45, "j4": 0, "j5": 90, "j6": 0})
    expected = reach.generic_cartesian(0, -45, 45, 0, 90, 0)
    check("portable: joints are read through the generic arm", pose is not None and math.dist((pose.x, pose.y, pose.z), expected[:3]) < 1e-9)
    check("portable: x, y, z win over the joints", reach.portable_pose({"x": 1, "y": 2, "z": 3, "j1": 9}).z == 3)
    check("portable: no pose, no point", (reach.portable_pose({"j1": 1}), reach.portable_pose({"x": "a", "y": 1, "z": 1}), reach.portable_pose({"x": True, "y": 1, "z": 1})) == (None, None, None))
    check("portable: a non-finite number is not a pose", reach.portable_pose({"x": float("nan"), "y": 1, "z": 1}) is None)


def scaling():
    model = "AR4 (6-DOF)"
    base = reach.forward(model, 20, 30, -20)
    near = [reach.PortablePoint(*base), reach.PortablePoint(base[0] * 0.8, base[1] * 0.8, base[2])]
    fit = reach.find_scale(model, near)
    check("scale: a Work in reach is left as it is", (fit.scale, fit.fits, fit.remaining) == (1.0, True, 0))
    far = [reach.PortablePoint(base[0] * 1.6, base[1] * 1.6, base[2] * 1.6), reach.PortablePoint(*base)]
    over = reach.count_over(model, far, reach.DEFAULT_REACH_TOLERANCE_MM, 1.0)
    fit = reach.find_scale(model, far)
    check("scale: a Work out of reach is measured", over >= 1)
    check("scale: it is scaled to a factor in the 5 % steps that leaves nothing over", fit.fits and 0.1 <= fit.scale < 1.0 and abs(fit.scale * 20 - round(fit.scale * 20)) < 1e-6 and reach.count_over(model, far, reach.DEFAULT_REACH_TOLERANCE_MM, fit.scale) == 0, repr(fit))
    nothing = [reach.PortablePoint(5000, 5000, 5000)]
    fit = reach.find_scale(model, nothing)
    check("scale: when no factor fits it says so", (not fit.fits) or fit.scale <= 0.15, repr(fit))
    joints, residual = reach.solve_pose(model, reach.PortablePoint(*base, a=500, b=-500, c=0))
    check("scale: the wrist joints stay inside their range", all(joint_range_deg(model, k)[0] <= joints[k] <= joint_range_deg(model, k)[1] for k in joints) and residual < 0.5)


forward_matches_studio()
inverse_finds_poses()
portable_points()
scaling()
print(f"FAILURES: {failures}")
sys.exit(1 if failures else 0)
