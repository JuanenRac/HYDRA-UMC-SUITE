"""Real assertion-based coverage for CameraView's new IP-camera fields
(models.py) and CamerasPanel's own Source Type toggle + robot assignment
(ui/panels/cameras_panel.py) - the SUITE-side port of HYDRA-UMC-STUDIO's
own Config.tsx "Camera Setup" tab. Headless: a real
QApplication, no network connection, feeding a real HydraState through
SuiteController.active_state_changed the same way a real WS/REST update
would - not mocked at the Qt layer, only the network is never actually
opened. Same convention as verify_atc_tools_panel.py."""
import asyncio
import sys
import types

import qasync
from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite.app import SuiteController
from hydra_suite.models import RTSP_DEFAULT_PORT, CameraView, HydraState
from hydra_suite.ui.panels.cameras_panel import CamerasPanel


def _state_with_camera(camera: dict, robots: list[dict] | None = None) -> HydraState:
    return HydraState(
        {
            "activeControllerId": "c1",
            "controllers": [{"id": "c1", "robots": robots or [], "cameras": [camera]}],
        }
    )


def _run() -> None:
    # --- CameraView field-by-field round trip (models.py) -----------------
    cam = CameraView({"id": 1})
    assert cam.source_type == "usb", "undefined sourceType must read as usb"
    assert cam.assigned_robot_id is None
    assert cam.rtsp_port == RTSP_DEFAULT_PORT, "unset rtspPort must read as the real RTSP default (554), not 0"

    cam.set_source_type("ip")
    cam.set_ip_host("192.168.0.210")
    cam.set_rtsp_port(8554)
    cam.set_rtsp_path("/11")
    cam.set_ip_username("admin")
    cam.set_ip_password("admin123456")
    cam.set_assigned_robot_id(3)

    assert cam.source_type == "ip"
    assert cam.ip_host == "192.168.0.210"
    assert cam.rtsp_port == 8554
    assert cam.rtsp_path == "/11"
    assert cam.ip_username == "admin"
    assert cam.ip_password == "admin123456"
    assert cam.assigned_robot_id == 3
    assert isinstance(cam.raw["assignedRobotId"], int), "must be a real JSON number, not a string - STUDIO does a strict r.id === cam.assignedRobotId comparison"

    cam.set_assigned_robot_id(None)
    assert cam.assigned_robot_id is None
    assert "assignedRobotId" not in cam.raw

    # --- CamerasPanel: real Qt widget wiring, headless ---------------------
    app = QApplication.instance() or QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    controller = SuiteController()
    panel = CamerasPanel(controller)

    state = _state_with_camera(
        {"id": 1, "connected": False, "type": "USB Vision Camera", "yoloEnabled": False, "sourceType": "ip", "ipHost": "192.168.0.211", "rtspPort": 554, "rtspPath": "/11"},
        robots=[{"id": 5, "model": "AR3", "role": "Idle"}],
    )
    # CamerasPanel._current_camera() (pre-existing, real production code -
    # not something this test changes) reads through
    # controller.active_state, which in real usage always agrees with
    # whatever the signal just carried because add_server()/set_active()
    # update both together. A bare .emit() here wouldn't do that, so
    # register a minimal stub "connection" (only .state is ever read)
    # the same way a real HydraConnection would resolve, instead of
    # weakening the panel's own real lookup path for this test.
    async def _noop_push_state() -> None:
        return None

    controller.connections["c1"] = types.SimpleNamespace(state=state, push_state=_noop_push_state)
    controller._active_id = "c1"
    controller.active_state_changed.emit(state)
    loop.run_until_complete(asyncio.sleep(0))  # pump both Qt + any push_active_state() task the edit just scheduled

    assert 1 in panel._cards, "a card must exist for camera id 1"
    card = panel._cards[1]
    assert card._robot_combo.count() == 2, "None (Floating) + the one real robot"
    assert card._ip_button.isChecked() is True
    assert card._usb_button.isChecked() is False
    assert card._ip_host_edit.text() == "192.168.0.211"
    assert card._source_stack.currentIndex() == 1, "IP page must be showing, not the USB one"

    # Flip to USB via the panel's own real callback path (not the button
    # click signal directly - headless click() delivery is unreliable
    # without a shown window; _on_field_changed is what the click ends up
    # calling either way, so exercising it directly is the real behavior).
    panel._on_field_changed(1, "source_type", "usb")
    loop.run_until_complete(asyncio.sleep(0))  # pump both Qt + any push_active_state() task the edit just scheduled
    cam1 = panel._current_camera(1)
    assert cam1 is not None and cam1.source_type == "usb"

    # Assign the robot through the same real path the combo's own signal uses.
    panel._on_field_changed(1, "assigned_robot_id", 5)
    loop.run_until_complete(asyncio.sleep(0))  # pump both Qt + any push_active_state() task the edit just scheduled
    cam1 = panel._current_camera(1)
    assert cam1.assigned_robot_id == 5

    print("verify_cameras_panel: all real assertions passed")


if __name__ == "__main__":
    _run()
