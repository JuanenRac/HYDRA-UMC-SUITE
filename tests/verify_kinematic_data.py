# =============================================================================
# HYDRA-UMC SUITE - tests/verify_kinematic_data.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# assets/kinematic_data.json is the one table of joint ranges and home poses that this program and HYDRA-UMC-STUDIO
# share. Checks: the file is well formed, every robot of the registry has its entry, the home pose of each model is
# the one its kinematics start from, the ranges are what the program clamps with, and, when the repository of STUDIO
# sits next to this one, its copy of the file is the same.
# =============================================================================
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, ".")

from hydra_suite import kinematic_data
from hydra_suite.joint_limits import GENERIC_RANGE_DEG, JOINT_LIMITS_DEG, joint_range_deg
from hydra_suite.render.kinematics import ROBOT_REGISTRY

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def main() -> int:
    data = kinematic_data.load()
    models = data["models"]
    check("file: schema 1.0", data.get("schema_version"), "1.0")
    check("file: every listed model has six joints with a range that goes up", all(set(e["limits"]) == set(kinematic_data.JOINTS) and all(lo < hi for lo, hi in e["limits"].values()) for e in models.values()), True)
    registry = {name for name in ROBOT_REGISTRY if not name.startswith("Generic")}
    check("file: every robot of the registry (but the generic one) is in it, and nothing else", set(models), registry)
    check("limits: the table the program clamps with is the file", JOINT_LIMITS_DEG, kinematic_data.joint_limits())
    check("limits: a model that is not listed gets the generic range", joint_range_deg("Generic (6-DOF)", "j1"), GENERIC_RANGE_DEG)
    check("limits: a listed model gets its own", joint_range_deg("Parol6 (6-DOF)", "j1"), (-97.4, 187.4))
    wrong = [(model, joint) for model, pose in kinematic_data.home_poses().items() for joint, value in pose.items() if abs(ROBOT_REGISTRY[model].home_pose_deg.get(joint, 0.0) - value) > 1e-6]
    check("home: each model starts from the pose in the file", wrong, [])

    sdk_file = Path(os.environ.get("HYDRA_UMC_SDK_DIR") or Path(__file__).resolve().parents[2] / "HYDRA-UMC-SDK") / "contracts" / "kinematics.json"
    if sdk_file.is_file():
        check("sdk: the file is the document of the SDK", json.loads(sdk_file.read_text(encoding="utf-8")), data)
    else:
        print("skip sdk: the contracts of the SDK are not next to this repository")

    sibling = Path(__file__).resolve().parents[2] / "HYDRA-UMC-STUDIO" / "src" / "data" / "kinematicData.json"
    if sibling.is_file():
        check("sibling: the copy of STUDIO is the same file", json.loads(sibling.read_text(encoding="utf-8")), data)
    else:
        print("skip sibling: HYDRA-UMC-STUDIO is not next to this repository")
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
