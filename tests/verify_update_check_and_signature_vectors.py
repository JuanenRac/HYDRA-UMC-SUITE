# =============================================================================
# HYDRA-UMC SUITE - tests/verify_update_check_and_signature_vectors.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies, with no network beyond a small HTTP server on this machine: how versions are read and compared, the manifest
# reader (a file of another ecosystem or another project is refused), the settings file (a damaged value falls back), the
# fetcher (only https, or this machine), the whole check against a fetcher that fails or lies, and the signature check
# against the published test vectors of the algorithm and a seeded set of damaged signatures.
# =============================================================================
import json
import random
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, ".")

from hydra_suite import ed25519_verify, update_check as uc

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


# --- versions ------------------------------------------------------------------------------------------------------------
check("three parts", uc.parse_version("1.2.3"), (1, 2, 3, 0))
check("four parts", uc.parse_version(" 0.8.1.4 "), (0, 8, 1, 4))
check("not versions", [uc.parse_version(v) for v in ("", "1.2", "1.2.3.4.5", "v1.2.3", "1.2.x", "1.2.3-rc1", None, 5, ["1.2.3"], "1.2.3\n4")], [None] * 10)
check("an order that is numeric, not textual", (uc.compare("0.9.0", "0.10.0"), uc.compare("0.10.0", "0.9.0")), ("outdated", "ahead"))
check("the build part counts", (uc.compare("0.8.0.1", "0.8.0.2"), uc.compare("0.8.0", "0.8.0.0")), ("outdated", "current"))
check("a version that is not one is unknown", [uc.compare(a, b) for a, b in (("x", "1.0.0"), ("1.0.0", None), (None, None))], ["unknown"] * 3)

# --- the address and the manifest ----------------------------------------------------------------------------------
cfg = {"rawBase": "https://example.test/raw/", "owner": "Me", "branch": "dev", "manifestFile": "m.json"}
check("the address of a manifest, without a double slash", uc.manifest_url("Repo", cfg), "https://example.test/raw/Me/Repo/dev/m.json")
good = {"ecosystem": "HYDRA-UMC", "name": "HYDRA-UMC-SERVER", "version": "1.2.3"}
check("a manifest as text or as an object", (uc.manifest_version(json.dumps(good)), uc.manifest_version(good), uc.manifest_version(json.dumps(good).encode())), ("1.2.3",) * 3)
check("the expected name must match", (uc.manifest_version(good, "HYDRA-UMC-SERVER"), uc.manifest_version(good, "HYDRA-UMC-SUITE")), ("1.2.3", None))
check("another ecosystem is refused", uc.manifest_version({**good, "ecosystem": "URTC"}), None)
check("a damaged manifest is refused", [uc.manifest_version(b) for b in ("{", "[]", "null", "", 5, {"ecosystem": "HYDRA-UMC"}, {**good, "version": "next"}, {**good, "version": 3})], [None] * 8)

# --- the API of the server -------------------------------------------------------------------------------------------
check("the server speaks the needed API", (uc.api_state(2, 2), uc.api_state(9, 2), uc.api_state(1, 2)), ("ok", "ok", "too_old"))
check("the server did not say", [uc.api_state(v, 2) for v in (None, 0, -1, True, "2", 2.0)], ["unknown"] * 6)

# --- the settings file -----------------------------------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    folder = Path(tmp)
    check("no file: the safe defaults, and the check is off", uc.load_settings(folder / "none.json")["enabledByDefault"], False)
    (folder / "bad.json").write_text("{not json", encoding="utf-8")
    check("a damaged file: the defaults", uc.load_settings(folder / "bad.json"), uc._FALLBACK)
    (folder / "list.json").write_text("[1]", encoding="utf-8")
    check("a file that is not an object: the defaults", uc.load_settings(folder / "list.json"), uc._FALLBACK)
    (folder / "ok.json").write_text(json.dumps({"enabledByDefault": True, "owner": " Someone ", "timeoutSeconds": 3, "branch": "", "minRemoteApiVersion": 0, "rawBase": 5, "serverRepository": "S"}), encoding="utf-8")
    loaded = uc.load_settings(folder / "ok.json")
    check("good values are taken and trimmed", (loaded["enabledByDefault"], loaded["owner"], loaded["timeoutSeconds"], loaded["serverRepository"]), (True, "Someone", 3, "S"))
    check("blank, zero and wrongly typed values fall back", (loaded["branch"], loaded["minRemoteApiVersion"], loaded["rawBase"]), (uc._FALLBACK["branch"], uc._FALLBACK["minRemoteApiVersion"], uc._FALLBACK["rawBase"]))
    (folder / "bool.json").write_text(json.dumps({"timeoutSeconds": True, "enabledByDefault": 1}), encoding="utf-8")
    loaded = uc.load_settings(folder / "bool.json")
    check("a boolean is not a number and a number is not a boolean", (loaded["timeoutSeconds"], loaded["enabledByDefault"]), (uc._FALLBACK["timeoutSeconds"], False))
check("the shipped settings keep the check off by default", uc.SETTINGS["enabledByDefault"], False)

# --- the fetcher: only https, or this machine -------------------------------------------------------------------------------
for url in ("http://example.com/x", "ftp://example.com/x", "file:///etc/passwd", "//example.com/x", "javascript:1", "HTTPS://EXAMPLE.COM"):
    try:
        uc.fetch_text(url, 1)
        outcome = "opened"
    except ValueError:
        outcome = "refused"
    except Exception as error:  # noqa: BLE001
        outcome = type(error).__name__
    check(f"refused before any connection: {url}", outcome, "refused")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = (b"x" * 300000) if self.path == "/big" else json.dumps(good).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
check("a small answer is read", json.loads(uc.fetch_text(base + "/m", 3))["version"], "1.2.3")
check("an answer is cut at 256 KiB", len(uc.fetch_text(base + "/big", 3)), 256 * 1024)
server.shutdown()
server.server_close()

# --- the whole check -----------------------------------------------------------------------------------------------------------
settings = {**uc._FALLBACK, "suiteRepository": "SUITE", "serverRepository": "SERVER"}


def fetcher(table):
    asked = []

    def fetch(url, timeout):
        asked.append(url)
        value = table[url.split("/")[-3]]
        if isinstance(value, Exception):
            raise value
        return value

    fetch.asked = asked
    return fetch


def manifest(name, version):
    return json.dumps({"ecosystem": "HYDRA-UMC", "name": name, "version": version})


fetch = fetcher({"SUITE": manifest("SUITE", "0.7.0"), "SERVER": manifest("SERVER", "2.0.0")})
result = uc.run_check("0.6.0", [{"name": "cm5", "appVersion": "2.0.0", "remoteApiVersion": 3}, {"name": "old", "appVersion": "1.0.0", "remoteApiVersion": 1}], fetch, settings)
check("the program is behind", result["suite"], {"installed": "0.6.0", "latest": "0.7.0", "state": "outdated"})
check("one server is current and one is behind", [(s["name"], s["state"], s["api"]) for s in result["servers"]], [("cm5", "current", "ok"), ("old", "outdated", "too_old")])
check("each manifest is read once", len(fetch.asked), 2)
check("no errors", result["errors"], [])

fetch = fetcher({"SUITE": manifest("SUITE", "0.7.0"), "SERVER": manifest("SERVER", "2.0.0")})
uc.run_check("0.7.0", [], fetch, settings)
check("with no server the server manifest is not read", len(fetch.asked), 1)

fetch = fetcher({"SUITE": OSError("no route"), "SERVER": manifest("OTHER", "2.0.0")})
result = uc.run_check("0.7.0", [{"name": "", "appVersion": None, "remoteApiVersion": "3"}], fetch, settings)
check("a failed fetch is unknown, with its reason", (result["suite"]["state"], result["suite"]["latest"], result["errors"][0]), ("unknown", None, "SUITE: no route"))
check("a manifest of another project is an error", result["errors"][1], "SERVER: not a manifest of this ecosystem")
check("a nameless server with no version is shown with placeholders", result["servers"][0], {"name": "?", "installed": "", "latest": None, "state": "unknown", "apiVersion": 0, "api": "unknown"})

# --- the signature check: published vectors and damaged signatures ---------------------------------------------------------------
V1 = (
    "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
    "",
    "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b",
)
V2 = (
    "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
    "72",
    "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00",
)
for index, (public, message, signature) in enumerate((V1, V2), 1):
    public, message, signature = bytes.fromhex(public), bytes.fromhex(message), bytes.fromhex(signature)
    check(f"vector {index} verifies", ed25519_verify.verify(public, message, signature), True)
    check(f"vector {index}: another message is refused", ed25519_verify.verify(public, message + b"x", signature), False)
    check(f"vector {index}: another key is refused", ed25519_verify.verify(bytes.fromhex(V2[0] if index == 1 else V1[0]), message, signature), False)
    rng = random.Random(1000 + index)
    refused = 0
    for _ in range(40):
        damaged = bytearray(signature)
        damaged[rng.randrange(64)] ^= 1 << rng.randrange(8)
        refused += ed25519_verify.verify(public, message, bytes(damaged)) is False
    check(f"vector {index}: every one of 40 single-bit damages is refused", refused, 40)
    check(f"vector {index}: wrong lengths are refused, not raised", [ed25519_verify.verify(public, message, signature[:n]) for n in (0, 1, 63)] + [ed25519_verify.verify(public[:31], message, signature)], [False] * 4)
public, message, signature = (bytes.fromhex(V1[0]), b"", bytes.fromhex(V1[2]))
check("a signature over the group order is refused", ed25519_verify.verify(public, message, signature[:32] + b"\xff" * 32), False)
check("a key that is not a point is refused", ed25519_verify.verify(b"\xff" * 32, message, signature), False)

print("UPDATE_CHECK_AND_SIGNATURE_VECTORS=" + ("PASS" if failures == 0 else f"FAIL {failures}"))
sys.exit(1 if failures else 0)
