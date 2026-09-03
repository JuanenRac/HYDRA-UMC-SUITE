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
        # 2 real paths found, not just 1 - exercises the real multi-stream
        # picker (ip_stream_labels()), not just the single-path case.
        return 200, {"ok": True, "paths": ["/11", "/12"], "triedPaths": ["/11", "/12", "/profile0"]}

    async def _fake_camera_status() -> tuple[int, object]:
        return 200, {"c1:1": {"status": "running", "lastError": None, "port": 8100}}

    # Real call log, not just a canned response - the PTZ assertions below
    # need to confirm _send_ptz() actually forwards THIS camera's own real
    # ip_host/username/password, not just that it returns ok.
    ptz_calls: list[tuple] = []

    async def _fake_send_ptz(camera_id: int, host: str, username: str, password: str, pan: int, tilt: int, zoom: int) -> tuple[int, object]:
        ptz_calls.append((camera_id, host, username, password, pan, tilt, zoom))
        return 200, {"ok": True}

    controller.connections["c1"] = types.SimpleNamespace(
        state=state,
        push_state=_noop_push_state,
        discover_usb_devices=_fake_discover_usb,
        discover_rtsp_path=_fake_discover_rtsp,
        fetch_camera_status=_fake_camera_status,
        send_ptz=_fake_send_ptz,
        # Real HydraConnection.info always has this - only needed here
        # since _on_type_combo_changed's own real stream-switch behavior
        # (card._get_stream_url() -> conn.info.base_url) is now exercised
        # directly by this test, not just the network-call methods above.
        info=types.SimpleNamespace(base_url="http://fake-test-server"),
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
    # No real "Discover Path" has run for this camera yet at this point -
    # ip_stream_labels() honestly offers only Main until discovery
    # actually confirms more real streams exist (see its own header
    # comment) - never assumes a fixed pair.
    assert ip_options == [CAMERA_TYPES[1], *CAMERA_TYPES[3:]], f"unexpected IP-mode options before any discovery: {ip_options}"

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
    # "stopped" - a real, deliberate state (the connected toggle is off,
    # the server already stopped the real process), never an error -
    # must render in the neutral grey reserved for it, not the red
    # _STATUS_COLORS["error"] a status this module doesn't recognize
    # would otherwise fall back to.
    card.update_status({"status": "stopped", "lastError": None})
    assert "●" in card._status_badge.text()
    assert "#8a97a6" in card._status_badge.styleSheet()
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
    assert cam1.discovered_stream_paths == ["/11", "/12"], "every real found path must be recorded, not just the first"
    assert cam1.rtsp_path == "/11", "the FIRST discovered path (main) must be the default"
    assert cam1.camera_type == "IP Vision Camera Main Stream", "a fresh discovery must reset the selection to Main"
    assert "/11" in card._discovery_status_label.text() and "/12" in card._discovery_status_label.text()

    # --- real multi-stream picker (matches CamerasView.tsx's own combobox
    # split, but now driven by ip_stream_labels() instead of a fixed pair) ---
    # Camera is still nominally "usb" here (the Thermal-survival block
    # above ended on it) - discovery itself doesn't require IP mode, but
    # the combobox split does, so flip back to IP first.
    card._on_source_type_clicked("ip")
    loop.run_until_complete(asyncio.sleep(0))
    panel._on_state_changed(controller.active_state)  # real refresh(), same as a server echo would trigger
    two_stream_options = [card._type_combo.itemText(i) for i in range(card._type_combo.count())]
    assert two_stream_options == ["IP Vision Camera Main Stream", "IP Vision Camera Sub Stream", *CAMERA_TYPES[3:]], (
        f"unexpected 2-stream options: {two_stream_options}"
    )

    # Selecting "Sub Stream" must be a REAL behavior change, not just a
    # label - it has to re-point rtsp_path at the real 2nd stream found.
    card._on_type_combo_changed("IP Vision Camera Sub Stream")
    loop.run_until_complete(asyncio.sleep(0))
    cam1 = panel._current_camera(1)
    assert cam1.rtsp_path == "/12", "picking the Sub Stream option must switch rtsp_path to the real 2nd discovered path"
    assert cam1.camera_type == "IP Vision Camera Sub Stream"

    # A camera with 3+ real discovered streams gets numbered Sub options,
    # per the user's own spec (Main, Sub 1, Sub 2, ...).
    panel._on_field_changed(1, "discovered_stream_paths", ["/11", "/12", "/13"])
    panel._on_state_changed(controller.active_state)
    three_stream_options = [card._type_combo.itemText(i) for i in range(card._type_combo.count())]
    assert three_stream_options == [
        "IP Vision Camera Main Stream", "IP Vision Camera Sub Stream 1", "IP Vision Camera Sub Stream 2", *CAMERA_TYPES[3:],
    ], f"unexpected 3-stream options: {three_stream_options}"
    card._on_type_combo_changed("IP Vision Camera Sub Stream 2")
    loop.run_until_complete(asyncio.sleep(0))
    cam1 = panel._current_camera(1)
    assert cam1.rtsp_path == "/13", "Sub Stream 2 must map to the real 3rd discovered path"

    # --- real extra path fields (Setup Camera parity with STUDIO's own
    # Config.tsx - a camera with 2+ real streams must show/edit ALL of
    # them, not just the primary field) ---
    assert not card._extra_path_edits[0].isHidden() and not card._extra_path_edits[1].isHidden()
    assert card._extra_path_edits[2].isHidden(), "only 2 extra fields (indices 1,2 of 3 real paths) may show for a 3-path camera"
    assert card._extra_path_edits[0].text() == "/12"
    assert card._extra_path_edits[1].text() == "/13"
    assert card._extra_path_labels[1].text() == "IP Vision Camera Sub Stream 2"

    # Editing the currently-INACTIVE extra field (index 1 = Sub Stream 1,
    # "/12") must only update its own stored path, not the live rtsp_path
    # (still pointed at Sub Stream 2, "/13", from the switch above).
    card._extra_path_edits[0].setText("/12-edited")
    card._on_extra_path_edited()
    loop.run_until_complete(asyncio.sleep(0))
    cam1 = panel._current_camera(1)
    assert cam1.discovered_stream_paths[1] == "/12-edited"
    assert cam1.rtsp_path == "/13", "editing a non-active stream's path must not touch the live rtsp_path"

    # Editing the currently-ACTIVE extra field (index 2 = Sub Stream 2,
    # the one selected above) must also update the live rtsp_path.
    card._extra_path_edits[1].setText("/13-edited")
    card._on_extra_path_edited()
    loop.run_until_complete(asyncio.sleep(0))
    cam1 = panel._current_camera(1)
    assert cam1.discovered_stream_paths[2] == "/13-edited"
    assert cam1.rtsp_path == "/13-edited", "editing the currently-active stream's path must update the live rtsp_path too"

    # --- real PTZ control (IP-only, matches CamerasView.tsx's own D-pad
    # toggle placed between the power and YOLOv8 buttons) --------------------
    cam1 = panel._current_camera(1)
    assert cam1.source_type == "ip", "camera must still be IP at this point in the test"
    assert not card._ptz_button.isHidden(), "PTZ toggle must show for an IP camera"
    assert card._ptz_row.isHidden(), "the direction/zoom pad stays collapsed until the toggle is checked"
    card._ptz_button.setChecked(True)
    assert not card._ptz_row.isHidden(), "checking the PTZ toggle must reveal the direction/zoom pad"

    loop.run_until_complete(card._send_ptz(60, 0, 0))
    assert ptz_calls[-1] == (1, cam1.ip_host, cam1.ip_username, cam1.ip_password, 60, 0, 0), (
        f"PTZ must forward this camera's own real host/credentials, got {ptz_calls[-1]}"
    )
    assert card._ptz_status_label.isHidden(), "a real ok:true response must not show an error"

    # A camera with no real PTZ hardware answers honestly - the server
    # reports a real error instead of pretending the move worked, and the
    # card must surface it, not swallow it.
    async def _fake_send_ptz_unsupported(camera_id, host, username, password, pan, tilt, zoom):
        return 502, {"ok": False, "error": "camera answered the PTZ request with HTTP 404"}

    controller.connections["c1"].send_ptz = _fake_send_ptz_unsupported
    loop.run_until_complete(card._send_ptz(0, 60, 0))
    assert not card._ptz_status_label.isHidden(), "a real PTZ failure must be shown, not swallowed"
    assert "404" in card._ptz_status_label.text()

    # Flip to USB - the PTZ toggle (and its own pad) must hide itself, not
    # leave an IP-only control sitting active on a USB camera.
    card._on_source_type_clicked("usb")
    loop.run_until_complete(asyncio.sleep(0))
    panel._on_state_changed(controller.active_state)
    assert card._ptz_button.isHidden(), "PTZ toggle must hide for a USB camera"
    assert card._ptz_row.isHidden()

    print("verify_cameras_panel: all real assertions passed")


if __name__ == "__main__":
    _run()
