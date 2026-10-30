# =============================================================================
# HYDRA-UMC SUITE - tests/verify_totp.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies the second step of the sign-in without a real server or window: how the answers are read, the sentence for
# each refusal, the QR encoder (structure, and that it draws the same symbol as the web program for known texts), and,
# against a small HTTP server on localhost, that a sign-in sends the code once and forgets it, that a session is not
# renewed and repeated on a wrong password, and that the requests of the second step are the ones the server has.
# =============================================================================
import asyncio
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, ".")

from hydra_suite.i18n import _
from hydra_suite.models import ServerInfo
from hydra_suite.net.client import HydraConnection
from hydra_suite.panel_logic import totp
from hydra_suite.panel_logic.qr_code import QR_MAX_BYTES, encode_qr, qr_svg_path

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


URI = "otpauth://totp/HYDRA-UMC:admin?secret=JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP&issuer=HYDRA-UMC&algorithm=SHA1&digits=6&period=30"

# --- reading the answers -------------------------------------------------------------------------
check("state", (totp.parse_status({"enabled": True, "recoveryLeft": 7}), totp.parse_status({"enabled": False})), ((True, 7), (False, 0)))
check("a damaged state is refused", (totp.parse_status({"enabled": "yes"}), totp.parse_status(None), totp.parse_status([])), (None, None, None))
good = {"secret": "JBSWY3DPEHPK3PXP", "uri": "otpauth://totp/HYDRA-UMC:a?secret=JBSWY3DPEHPK3PXP"}
check("enrolment", totp.parse_enrolment(good), ("JBSWY3DPEHPK3PXP", good["uri"]))
check("an enrolment that is not an otpauth address or a base32 key is refused",
      (totp.parse_enrolment({**good, "uri": "https://example.com"}), totp.parse_enrolment({**good, "secret": "not base32!"})), (None, None))
check("recovery codes", totp.parse_recovery_codes({"recoveryCodes": ["0a1b2-c3d4e", "ffeed-00112"]}), ["0a1b2-c3d4e", "ffeed-00112"])
check("a recovery list with one odd code is refused",
      (totp.parse_recovery_codes({"recoveryCodes": ["0a1b2-c3d4e", "<x>"]}), totp.parse_recovery_codes({"recoveryCodes": []}), totp.parse_recovery_codes({})), (None, None, None))
check("the key by groups of four", totp.grouped_key("JBSWY3DPEHPK3PXP"), "JBSW Y3DP EHPK 3PXP")
check("codes as typed", (totp.normalize_code(" 123 456 "), totp.normalize_code("123-456"), totp.normalize_code("0A1B2-C3D4E")), ("123456", "123456", "0a1b2-c3d4e"))

# --- sentences ------------------------------------------------------------------------------------
check("a missing route", totp.failure_text(404), _("TOTP_ERR_UNSUPPORTED"))
check("the wait, with and without the header", (totp.failure_text(429, {}, "42"), totp.failure_text(429, {}, None)), (_("TOTP_ERR_WAIT", seconds=42), _("TOTP_ERR_WAIT", seconds=30)))
check("password versus code", (totp.failure_text(401, {"error": "Invalid credentials"}), totp.failure_text(401, {"error": "A current code or an unused recovery code is required"}),
                               totp.failure_text(401, {"totpRequired": True}), totp.failure_text(401, {"error": "x"}, password_call=False)),
      (_("TOTP_ERR_PASSWORD"), _("TOTP_ERR_CODE"), _("TOTP_ERR_CODE"), _("TOTP_ERR_CODE")))
check("the other refusals", (totp.failure_text(0), totp.failure_text(403), totp.failure_text(409), totp.failure_text(400), totp.failure_text(500)),
      (_("TOTP_ERR_NETWORK"), _("TOTP_ERR_FORBIDDEN"), _("TOTP_ERR_ALREADY"), _("TOTP_ERR_CODE"), _("TOTP_ERR_HTTP", status=500)))

# --- the QR encoder -------------------------------------------------------------------------------
check("size by text length", [len(encode_qr(text)) for text in ("hi", "x" * 14, "x" * 15, URI, "x" * QR_MAX_BYTES)], [21, 21, 25, 45, 57])
check("a text that does not fit", encode_qr("x" * (QR_MAX_BYTES + 1)), None)
matrix = encode_qr(URI)
n = len(matrix)
finder_ok = all(
    matrix[r0 + r][c0 + c] == (0 if max(abs(r - 3), abs(c - 3)) == 2 else 1)
    for r0, c0 in ((0, 0), (0, n - 7), (n - 7, 0)) for r in range(7) for c in range(7)
)
check("the three finder patterns", finder_ok, True)
check("the timing line and the dark module", (all(matrix[6][i] == (1 if i % 2 == 0 else 0) for i in range(8, n - 8)), matrix[n - 8][8]), (True, 1))


def format_word(m):
    cells = [(0, 8), (1, 8), (2, 8), (3, 8), (4, 8), (5, 8), (7, 8), (8, 8), (8, 7), (8, 5), (8, 4), (8, 3), (8, 2), (8, 1), (8, 0)]
    return sum(m[r][c] << i for i, (r, c) in enumerate(cells))


def bch_rest(value):
    rem = value << 10
    for i in range(14, 9, -1):
        if (rem >> i) & 1:
            rem ^= 0x537 << (i - 10)
    return rem


word = format_word(matrix) ^ 0x5412
check("the format word has a right error-correction code at level M", (bch_rest(word >> 10) == (word & 0x3FF), word >> 13), (True, 0))
path, side = qr_svg_path(encode_qr("hi"))
check("the drawing", (side, path.startswith("M4 4h1v1h-1z"), path.count("M") == sum(map(sum, encode_qr("hi")))), (29, True, True))
view = totp.qr_view(URI)
check("what the screen gets", (view["tooLong"], view["size"], len(view["modules"]), set("".join(view["modules"]))), (False, 53, 45, {"0", "1"}))
check("too long for a code", totp.qr_view("x" * 300)["tooLong"], True)

# --- against a small server ----------------------------------------------------------------------


class State:
    totp_on = True
    logins: list = []
    refreshes = 0
    calls: list = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, status, body, headers=None):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        State.calls.append(("GET", self.path, None, self.headers.get("Authorization", "")))
        if self.path == "/api/totp/status":
            return self._send(200, {"enabled": True, "recoveryLeft": 8})
        self._send(404, {})

    def do_DELETE(self):
        State.calls.append(("DELETE", self.path, None, ""))
        self._send(200, {"success": True})

    def do_POST(self):
        body = self._body()
        State.calls.append(("POST", self.path, body, self.headers.get("Authorization", "")))
        if self.path == "/api/login":
            State.logins.append(body)
            if State.totp_on and body.get("totp") != "123456":
                return self._send(401, {"error": "A second-factor code is required" if "totp" not in body else "Invalid credentials", "totpRequired": True})
            return self._send(200, {"success": True, "token": "jwt-1", "refreshToken": "r-1", "role": "admin"})
        if self.path == "/api/refresh":
            State.refreshes += 1
            return self._send(200, {"success": True, "token": "jwt-2", "refreshToken": "r-2", "role": "admin"})
        if self.path == "/api/totp/disable":
            return self._send(401, {"error": "Invalid credentials"})
        if self.path == "/api/totp/confirm":
            return self._send(429, {"error": "wait"}, {"Retry-After": "17"})
        self._send(404, {})


async def run():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    conn = HydraConnection(ServerInfo(host="127.0.0.1", port=port, username="ana", password="pw"))
    details = []
    conn.login_changed.connect(lambda ok, detail: details.append((ok, detail)))
    check("sign-in without the code is refused and says the second step is needed", (await conn.login(), conn.needs_totp, details[-1][1]), (False, True, _("MSG_NET_LOGIN_NEEDS_CODE")))
    check("a refused sign-in is not retried by the reconnect loop", conn._login_rejected, True)
    check("no code was sent the first time", "totp" in State.logins[0], False)

    conn.totp_code = "123 456"
    check("sign-in with the code works", (await conn.login(), conn.needs_totp, conn.role), (True, False, "admin"))
    check("the code was sent as six digits", State.logins[1].get("totp"), "123456")
    check("and forgotten after it was sent", conn.totp_code, "")

    conn.totp_code = "000000"
    conn.info.password = "pw"
    wrong = await conn.login()
    check("a wrong code is refused with the server's own message", (wrong, details[-1][1]), (False, "Invalid credentials"))

    # a wrong password on a signed-in session must not renew the session and send the request a second time
    conn._token = "jwt-1"
    State.calls.clear()
    status, body, retry = await conn.totp_call("POST", "/api/totp/disable", {"password": "bad", "code": "1"})
    check("a 401 is an answer, not a reason to renew and repeat", (status, State.refreshes, len([c for c in State.calls if c[1] == "/api/totp/disable"])), (401, 0, 1))
    status, body, retry = await conn.totp_call("POST", "/api/totp/confirm", {"code": "1"})
    check("the wait the server asks for is passed on", (status, retry, totp.failure_text(status, body, retry)), (429, "17", _("TOTP_ERR_WAIT", seconds=17)))
    status, body, retry = await conn.totp_call("GET", "/api/totp/status")
    check("the state is read with the session token", (status, totp.parse_status(body), State.calls[-1][3]), (200, (True, 8), "Bearer jwt-1"))
    status, _body, _retry = await conn.reset_user_totp("ana lópez")
    check("an administrator's reset names the account", (status, State.calls[-1][:2]), (200, ("DELETE", "/api/users/ana%20l%C3%B3pez/totp")))
    check("a dead server is status 0", (await HydraConnection(ServerInfo(host="127.0.0.1", port=1)).totp_call("GET", "/api/totp/status"))[0], 0)
    server.shutdown()


asyncio.run(run())

print("FAILED" if failures else "ALL PASSED", failures)
sys.exit(1 if failures else 0)
