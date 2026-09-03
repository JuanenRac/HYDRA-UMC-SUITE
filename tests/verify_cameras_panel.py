"""Real assertion-based coverage for CameraView's new IP-camera fields
(models.py) and CamerasPanel's own Source Type toggle + robot assignment
(ui/panels/cameras_panel.py) - the SUITE-side port of HYDRA-UMC-STUDIO's
own Config.tsx "Camera Setup" tab, including the discover-USB/discover-RTSP-path
buttons and the real per-camera status badge added alongside
HYDRA-UMC-SERVER's own camera-process supervisor. Headless: a real
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
from hydra_suite.models import CAMERA_TYPES, RTSP_DEFAULT_PORT, CameraView, HydraState
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

    # Real canned responses for the 3 new discovery/status endpoints,
    # same (status, body) tuple shape HydraConnection._request_json()
    # returns for a real 200 - only the network transport is stubbed,
    # not the parsing/UI logic that consumes it.
    async def _fake_discover_usb() -> tuple[int, object]:
        return 200, {"devices": [{"index": 0, "available": True, "width": 640, "height": 480}]}

    async def _fake_discover_rtsp(host: str, port: int, username: str, password: str) -> tuple[int, object]:
        return 200, {"ok": True, "path": "/profile0", "status": 200, "triedPaths": ["/11", "/12", "/profile0"]}

    async def _fake_camera_status() -> tuple[int, object]:
        return 200, {"c1:1": {"status": "running", "lastError": None, "port": 8100}}

    controller.connections["c1"] = types.SimpleNamespace(
        state=state,
        push_state=_noop_push_state,
        discover_usb_devices=_fake_discover_usb,
        discover_rtsp_path=_fake_discover_rtsp,
        fetch_camera_status=_fake_camera_status,
    )
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

    # --- type combobox context-sensitivity (matches CamerasView.tsx's own
    # combobox split - see cameras_panel.py's own _sync_type_options()) ---
    # _on_field_changed() (used above) never calls refresh() itself - only
    # a fresh state broadcast does, same as real usage (an edit round-trips
    # through the server before the UI re-syncs). Force that re-sync here
    # the same way a real WS "state" echo would.
    panel._on_state_changed(controller.active_state)
    # Card is USB now (flipped above) - options must be USB + the 3
    # Thermal entries, never either IP stream option.
    usb_options = [card._type_combo.itemText(i) for i in range(card._type_combo.count())]
    assert usb_options == [CAMERA_TYPES[0], *CAMERA_TYPES[3:]], f"unexpected USB-mode options: {usb_options}"

    # Flip back to IP through the real button-click handler (not
    # _on_field_changed directly this time - _on_source_type_clicked is
    # itself the thing under test here, since it's the one that also
    # auto-normalizes `type`).
    card._on_source_type_clicked("ip")
    loop.run_until_complete(asyncio.sleep(0))
    cam1 = panel._current_camera(1)
    assert cam1.source_type == "ip"
    assert cam1.camera_type == "IP Vision Camera Main Stream", "switching USB -> IP must auto-normalize a stale USB type label"

    panel._on_state_changed(controller.active_state)  # real refresh(), same as a server echo would trigger
    ip_options = [card._type_combo.itemText(i) for i in range(card._type_combo.count())]
    assert ip_options == [CAMERA_TYPES[1], CAMERA_TYPES[2], *CAMERA_TYPES[3:]], f"unexpected IP-mode options: {ip_options}"

    # A Thermal selection must survive a source-type toggle unchanged
    # (never auto-normalized away) - see _on_source_type_clicked's own comment.
    panel._on_type_changed(1, "Thermal (MLX90640)")
    card._on_source_type_clicked("usb")
    loop.run_until_complete(asyncio.sleep(0))
    cam1 = panel._current_camera(1)
    assert cam1.camera_type == "Thermal (MLX90640)", "a Thermal type must never be auto-normalized away by a source-type toggle"

    # --- real per-camera status badge (GET /api/cameras/status) -----------
    card.update_status({"status": "running", "lastError": None, "port": 8100})
    assert "●" in card._status_badge.text() and card._status_badge.toolTip() == ""
    card.update_status({"status": "error", "lastError": "connection refused"})
    assert card._status_badge.toolTip() == "connection refused"
    card.update_status(None)
    assert card._status_badge.text() == ""

    # Real polling round trip through CamerasPanel._poll_camera_status(),
    # against the fake HydraConnection.fetch_camera_status() registered above.
    loop.run_until_complete(panel._poll_camera_status())
    assert panel._camera_status.get("c1:1", {}).get("status") == "running"
    assert "●" in card._status_badge.text()

    # --- real discovery round trips (against the fake HydraConnection
    # methods registered above - only the transport is fake, the button ->
    # asyncio.ensure_future() -> field-update wiring is exercised for real) ---
    loop.run_until_complete(card._discover_usb())
    assert card._usb_devices_combo.count() == 1
    assert card._usb_devices_combo.itemData(0) == 0
    card._on_usb_device_picked(0)
    cam1 = panel._current_camera(1)
    assert cam1.hardware_source, "picking a discovered USB device must fill hardware_source"

    card._ip_host_edit.setText("192.168.0.203")
    loop.run_until_complete(card._discover_rtsp())
    cam1 = panel._current_camera(1)
    assert cam1.rtsp_path == "/profile0", "a real discovered path must be written back through _on_field_changed"
    assert "profile0" in card._discovery_status_label.text()

    print("verify_cameras_panel: all real assertions passed")


if __name__ == "__main__":
    _run()
