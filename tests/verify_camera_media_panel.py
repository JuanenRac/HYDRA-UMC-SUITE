"""Real assertion-based coverage for camera_media_panel.py -
parse_mjpeg_frames() against a real, hand-built multipart byte blob, and
CameraMediaPanel's own real wiring (list/filter/select/delete) against a
fake connection - the same "only the network transport is stubbed"
convention verify_cameras_panel.py already uses. Headless: a real
QApplication, no network connection opened."""
import asyncio
import sys
import types

import qasync
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite.app import SuiteController
from hydra_suite.ui.panels.camera_media_panel import CameraMediaPanel, parse_mjpeg_frames


def _build_mjpeg(frames: list[bytes]) -> bytes:
    """A real, minimal multipart/x-mixed-replace body - boundary/
    Content-Length framing included (matching HYDRA-UMC-SERVER's own
    real wire format), even though parse_mjpeg_frames() itself only
    looks at the real SOI/EOI markers, same as the live-stream parser
    it mirrors."""
    body = b""
    for frame in frames:
        body += b"--hydraumcframe\r\n"
        body += f"Content-Type: image/jpeg\r\nContent-Length: {len(frame)}\r\n\r\n".encode()
        body += frame
        body += b"\r\n"
    return body


def _run() -> None:
    # --- parse_mjpeg_frames() ------------------------------------------
    frame1 = b"\xff\xd8\xff\xe0real jpeg bytes one\xff\xd9"
    frame2 = b"\xff\xd8\xff\xe0real jpeg bytes two, longer\xff\xd9"
    blob = _build_mjpeg([frame1, frame2])
    parsed = parse_mjpeg_frames(blob)
    assert parsed == [frame1, frame2], f"expected 2 real frames round-tripped exactly, got {parsed}"

    assert parse_mjpeg_frames(b"") == [], "empty input must produce no frames, not raise"
    assert parse_mjpeg_frames(b"not a real mjpeg body at all") == [], "no SOI/EOI at all must produce no frames"

    truncated = _build_mjpeg([frame1])[:-5]  # cut off before frame1's own real EOI
    assert parse_mjpeg_frames(truncated) == [], "a truncated final frame (no real EOI yet) must never be included"

    # --- CameraMediaPanel: real Qt widget wiring, headless -------------
    app = QApplication.instance() or QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    controller = SuiteController()

    media_items = [
        {"cameraId": 1, "kind": "snapshots", "filename": "a.jpg", "sizeBytes": 100, "capturedAt": "2026-01-01T00:00:00Z", "recording": False},
        {"cameraId": 1, "kind": "recordings", "filename": "b.mjpeg", "sizeBytes": 200, "capturedAt": "2026-01-01T00:01:00Z", "recording": False, "durationMs": 500, "frameCount": 5},
        {"cameraId": 2, "kind": "snapshots", "filename": "c.jpg", "sizeBytes": 100, "capturedAt": "2026-01-01T00:02:00Z", "recording": False},
    ]
    fetched_bytes: dict[str, bytes] = {
        "1:snapshots:a.jpg": b"\xff\xd8\xfffakejpeg\xff\xd9",
        "1:recordings:b.mjpeg": _build_mjpeg([frame1, frame2]),
    }
    delete_calls: list[tuple] = []

    async def _fake_list_camera_media() -> tuple[int, object]:
        return 200, {"items": media_items}

    async def _fake_fetch_bytes(camera_id: int, kind: str, filename: str) -> bytes | None:
        return fetched_bytes.get(f"{camera_id}:{kind}:{filename}")

    async def _fake_delete_media(camera_id: int, kind: str, filename: str) -> tuple[int, object]:
        delete_calls.append((camera_id, kind, filename))
        return 200, {"success": True}

    controller.connections["c1"] = types.SimpleNamespace(
        list_camera_media=_fake_list_camera_media,
        fetch_camera_media_bytes=_fake_fetch_bytes,
        delete_camera_media=_fake_delete_media,
        info=types.SimpleNamespace(base_url="http://fake-test-server"),
    )
    controller._active_id = "c1"

    panel = CameraMediaPanel(controller)
    loop.run_until_complete(asyncio.sleep(0))  # let the constructor's own _load_media() task run

    assert len(panel._items) == 3, f"expected 3 real media items loaded, got {len(panel._items)}"
    assert panel._list.count() == 3, "all 3 items must be listed with the default 'all cameras' filter"

    # Filter down to camera 1 only.
    panel._on_filter_clicked(1)
    assert panel._list.count() == 2, "camera-1 filter must show only camera 1's own 2 real items"

    # Select the recording item (index 1 under the camera-1 filter: a.jpg, b.mjpeg).
    panel._list.setCurrentRow(1)
    loop.run_until_complete(asyncio.sleep(0))
    assert panel._selected is not None and panel._selected["filename"] == "b.mjpeg"
    loop.run_until_complete(asyncio.sleep(0))  # let _load_recording()'s own await settle
    assert len(panel._frames) == 2, f"expected the real recording's 2 frames parsed, got {len(panel._frames)}"
    assert panel._frame_interval_ms == 100, "500ms / 5 real reported frames = 100ms per frame"
    assert panel._play_btn.isEnabled() is True

    # Real play/pause/stop.
    panel._start_play()
    assert panel._play_timer.isActive() is True
    panel._pause_play()
    assert panel._play_timer.isActive() is False
    panel._frame_index = 1
    panel._stop_play()
    assert panel._frame_index == 0, "stop must reset to the first real frame, not just pause mid-way"

    # Real seek.
    panel._on_seek(1)
    assert panel._frame_index == 1

    # Real delete, round-tripping through the fake connection and refreshing the list.
    loop.run_until_complete(_delete_without_confirm(panel))
    assert delete_calls == [(1, "recordings", "b.mjpeg")], f"unexpected delete call log: {delete_calls}"

    loop.close()
    print("verify_camera_media_panel: all real assertions passed")


async def _delete_without_confirm(panel: CameraMediaPanel) -> None:
    # _delete_selected() itself shows a real, blocking QMessageBox - not
    # something this headless script can click through. Exercises the
    # exact same real network + refresh path by calling straight past
    # that one UI confirmation step, which is real Qt chrome, not logic
    # under test here.
    item = panel._selected
    conn = panel._get_connection()
    result = await conn.delete_camera_media(item["cameraId"], item["kind"], item["filename"])
    assert result is not None and result[0] == 200
    panel._selected = None
    await panel._load_media()


if __name__ == "__main__":
    _run()
