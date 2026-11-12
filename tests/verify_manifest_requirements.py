# =============================================================================
# HYDRA-UMC SUITE - tests/verify_manifest_requirements.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The `target` and `min_bootloader` an image's manifest entry states reach the flash request of the server:
#   - read from the component or the binary entry (the binary wins), a value the relay would refuse is dropped
#   - carried by the listing of a release and by flash_signing_options only when the manifest states them
#   - sent as query parameters of POST /api/hardware/canota/flash, and not sent when absent
#   - the option of the relay of the twin: read, locked by the environment, sent
# No network, no window.
# =============================================================================
import asyncio
import sys

sys.path.insert(0, ".")

from hydra_suite import can_ota
from hydra_suite.can_ota import CanOtaTarget, flash_signing_options, hardware_start_flash, manifest_flash_requirements
from hydra_suite.panel_logic import server_security as sec

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def main() -> int:
    check("component values are read", manifest_flash_requirements({"target": "g474", "min_bootloader": "0.1.7"}, {}), {"target": "g474", "min_bootloader": "0.1.7"})
    check("the binary entry wins", manifest_flash_requirements({"target": "g474", "min_bootloader": "0.1.7"}, {"target": "h745-cm7", "min_bootloader": "0.2.0"}), {"target": "h745-cm7", "min_bootloader": "0.2.0"})
    check("a manifest that states neither gives nothing", (manifest_flash_requirements({}, {}), manifest_flash_requirements(None, None)), ({}, {}))
    check("a value the relay would refuse is dropped", manifest_flash_requirements({"target": "a b/../c", "min_bootloader": "1.2"}, {"target": 7, "min_bootloader": ["1.0.0"]}), {})
    check("a malformed binary value falls back to the component", manifest_flash_requirements({"target": "g474"}, {"target": "??"}), {"target": "g474"})

    sig = "ab" * 64
    check("the signing options keep their old shape without requirements", flash_signing_options("0.2.5", "0.2.9", sig), {"version_patch": 5, "signature": sig, "downgrade_from": "0.2.9"})
    check("... and carry the requirements when given", flash_signing_options("0.3.0", None, None, {"target": "g474", "min_bootloader": "0.1.7"}),
          {"version_patch": 0, "signature": None, "downgrade_from": None, "target": "g474", "min_bootloader": "0.1.7"})
    check("... but not empty ones", flash_signing_options("0.3.0", None, None, {"target": None, "min_bootloader": ""}), {"version_patch": 0, "signature": None, "downgrade_from": None})

    seen: dict = {}

    class _Conn:
        async def canota_request(self, method, path, params=None, data=None, timeout=None):
            seen.clear()
            seen.update(params)
            return 200, {"success": True, "finalPhase": "done"}

    board = CanOtaTarget(tier="controllerBoard", controller_name="c", robot_index0=0)
    asyncio.run(hardware_start_flash(_Conn(), board, b"x", 0, 1, 1, flash_signing_options("0.1.9", None, None, {"target": "g474", "min_bootloader": "0.1.7"})))
    check("the request carries target and min_bootloader", (seen.get("target"), seen.get("min_bootloader")), ("g474", "0.1.7"))
    asyncio.run(hardware_start_flash(_Conn(), board, b"x", 0, 1, 1, flash_signing_options("0.1.9", None, None)))
    check("the request carries neither when the manifest states none", ("target" in seen, "min_bootloader" in seen), (False, False))
    asyncio.run(hardware_start_flash(_Conn(), board, b"x", 0, 1, 1, {"target": "bad value/", "min_bootloader": "1.2"}))
    check("a malformed value is not sent even if a caller passes it", ("target" in seen, "min_bootloader" in seen), (False, False))

    asset = can_ota.GithubFirmwareAsset(name="a.bin", url="u", size=1, release_tag="0.1.9", published_at="", target="g474", min_bootloader="0.1.7")
    check("the asset carries them", (asset.target, asset.min_bootloader), ("g474", "0.1.7"))
    check("the asset defaults to none", (can_ota.GithubFirmwareAsset(name="a", url="u", size=1, release_tag="1", published_at="").target,), (None,))

    import httpx

    api = "https://api.github.com/repos/JuanenRac/HYDRA-UMC/releases/"
    manifest = {"components": {"g474_application": {"display_name": "App", "chip": "G4", "version_string": "0.1.9", "hardware_id": "0x2", "target": "g474",
                                                   "files": {"bin": {"filename": "A.bin", "size_bytes": 2, "crc32": "0x2", "min_bootloader": "0.1.7"}}}}}
    release = {"published_at": "x", "assets": [{"name": "firmware_manifest.json", "url": api + "assets/1"}, {"name": "A.bin", "url": api + "assets/2"}]}

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/releases/latest"):
            return httpx.Response(200, json=release)
        if str(request.url).endswith("assets/1"):
            return httpx.Response(200, json=manifest)
        return httpx.Response(404)

    async def _listing():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await can_ota.fetch_release_asset_firmware("JuanenRac/HYDRA-UMC", "controllerBoard", client)

    listed = asyncio.run(_listing())
    check("the release listing reads them from the manifest", [(a.target, a.min_bootloader) for a in listed], [("g474", "0.1.7")])

    base = {"aiAccess": {"value": "open", "source": "default"}, "infoAuth": {"value": False, "source": "default"}, "tls": {"enabled": False, "source": "default"}}
    plain = sec.parse_state(base)
    check("relay switch: a server without the option shows none", (plain["twinRelay"], sec.view(plain)["twinRelayAvailable"]), (None, False))
    off = sec.parse_state({**base, "twinRelay": {"enabled": {"value": False, "source": "default"}}})
    locked = sec.parse_state({**base, "twinRelay": {"enabled": {"value": True, "source": "env"}}})
    check("relay switch: off by default", (sec.view(off)["twinRelayEnabled"], sec.view(off)["twinRelayEnabledLocked"]), (False, False))
    check("relay switch: fixed by the environment it is locked", (sec.view(locked)["twinRelayEnabled"], sec.view(locked)["twinRelayEnabledLocked"]), (True, True))
    check("relay switch: a damaged value shows none", sec.parse_state({**base, "twinRelay": {"enabled": {"value": "yes", "source": "default"}}})["twinRelay"], None)
    check("relay switch: what is sent", (sec.twin_relay_patch(True), sec.twin_relay_patch(False)), ({"twinRelay": {"enabled": True}}, {"twinRelay": {"enabled": False}}))
    check("relay switch: every key of the view exists without a server", set(sec.view(None)) == set(sec.view(locked)), True)

    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
