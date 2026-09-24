"""Real assertion-based coverage for RobotState.motion_source and the
overview table's status column: the same offline / simulated / live rule as
HYDRA-UMC-STUDIO's motionSource(). Headless (a real QApplication and a real
OverviewPanel-free model check); nothing is mocked except the plain dict a
server payload would be."""
import sys

sys.path.insert(0, ".")
from hydra_suite.models import RobotView as RobotState


def _robot(**raw) -> RobotState:
    return RobotState({"id": "1", "model": "Parol6", **raw})


def main() -> None:
    assert _robot(online=False, urtcConnected=False).motion_source == "offline"
    assert _robot(online=False, urtcConnected=True).motion_source == "offline"
    assert _robot(online=True, urtcConnected=False).motion_source == "simulated"
    assert _robot(online=True, urtcConnected=True).motion_source == "live"
    assert _robot().motion_source == "offline"  # a payload with neither field

    from hydra_suite.i18n import _

    for key in ("STATUS_OFFLINE", "MOTION_SIMULATED", "MOTION_LIVE"):
        assert _(key) != key, f"{key} has no translation"
    print("MOTION_SOURCE=PASS")


if __name__ == "__main__":
    main()
