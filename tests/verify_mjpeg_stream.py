"""Real assertion-based coverage for cameras_panel.py's own
iter_mjpeg_frames() - the SOI/EOI byte-scanning MJPEG client (2026-09,
mirrors HYDRA-UMC-ANDROID-CONTROL's own MjpegStreamParser.kt). Spins up
a real local HTTP server serving a real multipart/x-mixed-replace
stream (not mocked at the HTTP layer) and verifies the async generator
extracts exactly the real frames sent, byte-for-byte, including a
corrupt/oversized frame being skipped without killing the stream."""
import asyncio
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, ".")
from hydra_suite.ui.panels.cameras_panel import iter_mjpeg_frames, _MJPEG_MAX_FRAME_BYTES

SOI = b"\xff\xd8"
EOI = b"\xff\xd9"


def _fake_jpeg(payload: bytes) -> bytes:
    """A byte string that looks like one real JPEG frame to the SOI/EOI
    scanner - real markers, arbitrary payload in between (the scanner
    itself never inspects JPEG segment structure, only the two markers,
    so this is a faithful test double for its own real behavior)."""
    return SOI + payload + EOI


class _MjpegHandler(BaseHTTPRequestHandler):
    frames: list[bytes] = []

    def log_message(self, *args) -> None:
        pass  # keep test output clean - real server, just quiet

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=testboundary")
        self.end_headers()
        try:
            for frame in self.frames:
                self.wfile.write(b"--testboundary\r\nContent-Type: image/jpeg\r\n\r\n")
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _run() -> None:
    port = _free_port()
    real_frames = [_fake_jpeg(b"frame-one-payload"), _fake_jpeg(b"frame-two-different-payload"), _fake_jpeg(b"x" * 500)]
    _MjpegHandler.frames = real_frames

    server = ThreadingHTTPServer(("127.0.0.1", port), _MjpegHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        async def _collect():
            received = []
            async for frame in iter_mjpeg_frames(f"http://127.0.0.1:{port}/stream"):
                received.append(frame)
                if len(received) == len(real_frames):
                    break
            return received

        received = asyncio.run(_collect())
        assert received == real_frames, "must extract every real frame, byte-for-byte, in order"
        print(f"iter_mjpeg_frames: extracted {len(received)} real frames correctly: PASS")

        # --- oversized/corrupt frame is skipped, stream keeps going -------
        _MjpegHandler.frames = [
            _fake_jpeg(b"good-frame-before"),
            _fake_jpeg(b"z" * (_MJPEG_MAX_FRAME_BYTES + 1000)),  # too big - must be skipped, not crash the reader
            _fake_jpeg(b"good-frame-after"),
        ]

        async def _collect_with_oversized():
            received = []
            async for frame in iter_mjpeg_frames(f"http://127.0.0.1:{port}/stream"):
                received.append(frame)
                if len(received) == 2:
                    break
            return received

        received2 = asyncio.run(_collect_with_oversized())
        assert received2 == [_fake_jpeg(b"good-frame-before"), _fake_jpeg(b"good-frame-after")], \
            "oversized frame must be silently skipped, real frames before/after it still delivered"
        print("iter_mjpeg_frames: oversized/corrupt frame skipped, stream continues: PASS")

        # --- a genuinely dead server yields nothing, doesn't hang/raise ---
        async def _collect_from_nothing():
            received = []
            async for frame in iter_mjpeg_frames("http://127.0.0.1:1/stream"):  # nothing listens on port 1
                received.append(frame)
            return received

        received3 = asyncio.run(asyncio.wait_for(_collect_from_nothing(), timeout=15))
        assert received3 == [], "an unreachable server must end the generator cleanly, not raise"
        print("iter_mjpeg_frames: unreachable server ends cleanly: PASS")
    finally:
        server.shutdown()
        thread.join(timeout=5)

    print("ALL VERIFY_MJPEG_STREAM CHECKS PASSED")


if __name__ == "__main__":
    _run()
