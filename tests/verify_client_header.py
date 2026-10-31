# =============================================================================
# HYDRA-UMC SUITE - tests/verify_client_header.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The X-Hydra-Client header of this client: its type and, after a slash, its version ("suite/0.7.5").
#   - the type is always "suite" (the server compares the type only; the version goes to its history of connections)
#   - the version is the one of the package, and it is a version the server accepts (1 to 24 of 0-9 A-Z a-z . _ -)
#   - a version the server would not accept is left out and the header is just "suite"
#   - a request really sent carries the header
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, ".")

from hydra_suite import __version__
from hydra_suite.net import client

# the pattern the server uses for the whole value (src/connections.ts, CLIENT_HEADER)
SERVER_PATTERN = re.compile(r"^(studio|suite|android|ios|dsi|watch|voice)(?:/([0-9A-Za-z._-]{1,24}))?$")
FAILED: list[str] = []


def check(label, actual, expected):
    if actual != expected:
        FAILED.append(label)
        print(f"FAIL {label}: {actual!r} != {expected!r}")


def main() -> int:
    value = client.HYDRA_CLIENT_HEADERS["X-Hydra-Client"]
    check("the header is the only one sent", list(client.HYDRA_CLIENT_HEADERS), ["X-Hydra-Client"])
    check("the type is suite", value.split("/", 1)[0], "suite")
    check("the server accepts the value", SERVER_PATTERN.match(value) is not None, True)
    check("the version is the one of the package", value, f"suite/{__version__}")
    check("the server reads that version", SERVER_PATTERN.match(value).group(2), __version__)

    f = client.client_header_value
    check("a plain version", f("0.7.5"), "suite/0.7.5")
    check("a four part version", f("0.8.1.6"), "suite/0.8.1.6")
    check("the longest version the server takes", f("a" * 24), "suite/" + "a" * 24)
    for bad in (None, "", "a" * 25, "0.7 5", "0.7/5", "0.7\r\nX-Evil: 1", "v1,2", "versión", " 0.7.5", "0.7.5\n"):
        check(f"a version the server would not take is left out: {bad!r}", f(bad), "suite")

    # a request really sent carries the header
    seen: list[str | None] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            seen.append(self.headers.get("X-Hydra-Client"))
            body = json.dumps({}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        import httpx

        with httpx.Client(headers=client.HYDRA_CLIENT_HEADERS) as http:
            http.get(f"http://127.0.0.1:{server.server_port}/api/hydra-info")
    finally:
        server.shutdown()
    check("a request carries the header with the version", seen, [f"suite/{__version__}"])

    if FAILED:
        print(f"CLIENT_HEADER=FAIL {len(FAILED)}")
        return 1
    print("CLIENT_HEADER=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
