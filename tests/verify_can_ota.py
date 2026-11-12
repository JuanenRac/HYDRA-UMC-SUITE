"""Real assertion-based coverage for can_ota.py - the SUITE-side port of
HYDRA-UMC-STUDIO's own src/lib/canOta.ts. Covers the pure
helpers, the mock async generators (mock_flash/mock_self_test - run for
real, not stubbed, since they're fast enough headless), CRC32 against a
known real value, and resolve_hardware_target's own real tier-mapping
boundary (Tier 3 stays unreachable on purpose)."""
import asyncio
import sys
from urllib.parse import urlparse

sys.path.insert(0, ".")
from hydra_suite.can_ota import (
    CanOtaTarget,
    flash_preflight,
    FlashOptions,
    crc32,
    chip_name_for,
    has_advanced_expansion,
    hop_count,
    hop_description,
    mock_flash,
    mock_query_version,
    mock_self_test,
    resolve_hardware_target,
    slot_base_id,
    slot_label,
)


async def _none():
    return None


def _run() -> None:
    # --- pure helpers --------------------------------------------------
    assert slot_label(0) == "A1"
    assert slot_label(7) == "A8"
    assert slot_base_id(0) == 0x600
    assert slot_base_id(1) == 0x640 and slot_base_id(7) == 0x7C0  # the window of a slot is 64 identifiers wide

    assert hop_count("kinematicBrain") == 0
    assert hop_count("controllerBoard") == 1
    assert hop_count("urtcHead") == 2
    assert hop_count("urtcExpansion") == 3

    assert chip_name_for("kinematicBrain") == "STM32H745ZIT6"
    assert chip_name_for("urtcExpansion") == "STM32F303CBT6"

    assert has_advanced_expansion(3) is True
    assert has_advanced_expansion(4) is True
    assert has_advanced_expansion(0) is False
    assert has_advanced_expansion(None) is False

    # Real, known CRC32 (IEEE 802.3) for the ASCII bytes "123456789" is
    # the textbook check value 0xCBF43926 - confirms zlib.crc32 here
    # produces the exact same real algorithm STUDIO's own hand-rolled
    # table does, not a different/incompatible checksum.
    assert crc32(b"123456789") == 0xCBF43926
    print("pure helpers + real CRC32 check value: PASS")

    # --- hop_description -------------------------------------------------
    kb_target = CanOtaTarget(controller_name="HYDRA-UMC Master", tier="kinematicBrain")
    assert hop_description(kb_target) == "HYDRA-UMC Master -> SPI -> STM32H745ZIT6 (Kinematic Brain)"

    head_target = CanOtaTarget(controller_name="HYDRA-UMC Master", tier="urtcHead", robot_id=1, robot_name="Robot A1", robot_index0=0)
    desc = hop_description(head_target)
    assert "A1" in desc and "URTC Tool Head" in desc
    print("hop_description: PASS")

    # --- resolve_hardware_target - real tier-mapping boundary -------------
    assert resolve_hardware_target(kb_target).target_tier == 0  # SPI_TARGET_SELF
    board_target = CanOtaTarget(controller_name="c", tier="controllerBoard", robot_index0=3)
    resolved = resolve_hardware_target(board_target)
    assert resolved.target_slot == 3 and resolved.relay is False
    head_resolved = resolve_hardware_target(head_target)
    assert head_resolved.relay is True, "urtcHead must tunnel through the resolved Tier 1 target"
    expansion_target = CanOtaTarget(controller_name="c", tier="urtcExpansion", robot_index0=0)
    assert resolve_hardware_target(expansion_target) is None, "Tier 3 has no real tunnel hop yet - must stay unreachable"
    print("resolve_hardware_target real tier-mapping boundary: PASS")

    # --- mock_query_version - real async, not stubbed ----------------------
    async def _query():
        # Run enough times that the ~5% offline chance doesn't make this
        # test flaky either way - just check the shape is always sane.
        for _ in range(20):
            result = await mock_query_version(kb_target)
            assert isinstance(result.online, bool)
            if result.online:
                assert result.firmware_version is not None
                assert result.hardware_id.startswith("KB-")
    asyncio.run(_query())
    print("mock_query_version: PASS")

    # --- mock_flash - real async generator, full real run ------------------
    async def _flash():
        firmware = bytes(5000)  # 5000 bytes -> ceil(5000/2048) = 3 pages
        opts = FlashOptions(allow_downgrade=True, erase_fram=True)
        phases = []
        last_pages_total = None
        async for progress in mock_flash(kb_target, firmware, opts):
            phases.append(progress.phase)
            last_pages_total = progress.pages_total
        assert last_pages_total == 3
        assert phases[0] == "connecting"
        assert "erasing_fram" in phases, "eraseFram=True must produce that phase"
        assert phases.count("transferring") == 3, "one transferring event per page"
        # allow_downgrade=True disables the anti-rollback error path entirely.
        assert phases[-1] == "done"
    asyncio.run(_flash())
    print("mock_flash - real async generator, real page count from real byte length: PASS")

    # --- mock_self_test - step set varies by real tier ----------------------
    async def _self_test():
        steps = [s async for s in mock_self_test(kb_target)]
        ids = {s.id for s in steps}
        assert {"comm", "version", "spi", "fdcan"} <= ids, "kinematicBrain must include spi/fdcan steps"

        board_steps = [s async for s in mock_self_test(board_target)]
        board_ids = {s.id for s in board_steps}
        assert {"fram", "axes", "endstops"} <= board_ids, "controllerBoard must include fram/axes/endstops steps"
    asyncio.run(_self_test())
    print("mock_self_test - real per-tier step set: PASS")

    # --- signed flash: version, signature and downgrade ----------------------
    from hydra_suite.can_ota import flash_signing_options, normalize_signature, parse_version_full

    assert parse_version_full("v1.2.3-rc") == (1, 2, 3) and parse_version_full("0.9") == (0, 9, 0) and parse_version_full("x") is None
    sig = "Ab" * 64
    assert normalize_signature(sig + chr(10)) == sig.lower() and normalize_signature("abc") is None and normalize_signature(None) is None
    assert flash_signing_options("0.2.5", "0.2.9", sig) == {"version_patch": 5, "signature": sig.lower(), "downgrade_from": "0.2.9"}
    assert flash_signing_options("0.3.0", "0.2.9", None) == {"version_patch": 0, "signature": None, "downgrade_from": None}
    assert flash_signing_options("0.3.0", None, sig)["downgrade_from"] is None
    seen = {}

    class _Conn:
        async def canota_request(self, method, path, params=None, data=None, timeout=None):
            seen.update(params)
            return 200, {"success": True, "finalPhase": "done"}

    from hydra_suite.can_ota import hardware_start_flash

    result = asyncio.run(hardware_start_flash(_Conn(), board_target, b"x", 0, 2, 1, flash_signing_options("0.2.5", "0.2.9", sig)))
    assert result.success and seen["version_patch"] == 5 and seen["signature"] == sig.lower() and seen["downgrade_from"] == "0.2.9"
    print("signed flash parameters: PASS")

    from hydra_suite.can_ota import SLOT_FRAMES, SLOT_WINDOW

    offsets = list(SLOT_FRAMES.values())
    assert len(set(offsets)) == len(offsets) and all(o < SLOT_WINDOW for o in offsets)
    assert SLOT_FRAMES["relay_response"] != SLOT_FRAMES["relay_request"] and SLOT_FRAMES["relay_response_extra"] != SLOT_FRAMES["relay_request_extra"]
    print("slot frames: one identifier each, inside the window: PASS")

    from hydra_suite.can_ota import GithubFirmwareAsset, download_github_firmware, fetch_release_asset_firmware, sha256_from_digest
    import hashlib
    import httpx

    assert sha256_from_digest("sha256:" + "AB" * 32) == "ab" * 32 and sha256_from_digest("sha1:abc") is None and sha256_from_digest(None) is None
    manifest = {"components": {
        "g474_bootloader": {"display_name": "Boot", "chip": "G4", "version_string": "0.1.8", "hardware_id": "0x1", "files": {"bin": {"filename": "B.bin", "size_bytes": 1, "crc32": "0x1"}}},
        "g474_application": {"display_name": "App", "chip": "G4", "version_string": "0.1.9", "hardware_id": "0x2", "files": {"bin": {"filename": "A.bin", "size_bytes": 2, "crc32": "0x2"}}},
    }}
    api = "https://api.github.com/repos/JuanenRac/HYDRA-UMC/releases/"
    release = {"published_at": "x", "assets": [
        {"name": "firmware_manifest.json", "url": api + "assets/1"},
        {"name": "A.bin", "url": api + "assets/2", "digest": "sha256:" + "CD" * 32},
        {"name": "A.sig", "url": api + "assets/3"},
    ]}
    asked: list[tuple[str, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        asked.append((str(request.url), request.headers.get("accept")))
        if str(request.url).endswith("/releases/latest"):
            return httpx.Response(200, json=release)
        if str(request.url).endswith("assets/1"):
            return httpx.Response(200, json=manifest)
        if str(request.url).endswith("assets/3"):
            return httpx.Response(200, text=sig + chr(10))
        return httpx.Response(500)

    async def _release_listing():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await fetch_release_asset_firmware("JuanenRac/HYDRA-UMC", "controllerBoard", client)

    listed = asyncio.run(_release_listing())
    assert [a.name for a in listed] == ["A.bin"], listed
    assert listed[0].sha256 == "cd" * 32 and listed[0].signature == sig.lower() and listed[0].crc32 == "0x2" and listed[0].release_tag == "0.1.9"
    assert not any(urlparse(url).hostname == "raw.githubusercontent.com" for url, _ in asked)
    assert all(accept == "application/octet-stream" for url, accept in asked if "/assets/" in url)
    print("firmware listed from the latest release assets: PASS")

    good = b"image-bytes"
    real_client = httpx.AsyncClient

    class _Client(real_client):
        def __init__(self, *a, **k):
            super().__init__(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=good)))

    httpx.AsyncClient = _Client
    try:
        ok = GithubFirmwareAsset("A.bin", api + "assets/2", len(good), "1", "", sha256=hashlib.sha256(good).hexdigest())
        assert asyncio.run(download_github_firmware(ok)) == good
        bad = GithubFirmwareAsset("A.bin", api + "assets/2", len(good), "1", "", sha256="0" * 64)
        try:
            asyncio.run(download_github_firmware(bad))
            raise AssertionError("a wrong SHA-256 must be refused")
        except RuntimeError as exc:
            assert "SHA-256 mismatch" in str(exc)
    finally:
        httpx.AsyncClient = real_client
    print("download checks the SHA-256: PASS")

    # --- the checks before a flash over the real bus ---------------------
    assert flash_preflight("0x48374334", "v1.2.3", "1.2.3", False, False) is None
    assert flash_preflight(None, "v1.2.3", "1.2.3", False, False) == "no_hardware_id"
    assert flash_preflight("", "v1.2.3", None, False, False) == "no_hardware_id"
    assert flash_preflight("0", "v1.2.3", None, False, False) == "no_hardware_id"
    assert flash_preflight("nonsense", "v1.2.3", None, False, False) == "no_hardware_id"
    assert flash_preflight("0x1", None, None, False, False) == "no_version"
    assert flash_preflight("0x1", "latest", "1.0.0", True, False) == "no_version"
    assert flash_preflight("0x1", "v1.2.3", "1.2.3", False, True) == "fram_erase_unsupported"
    assert flash_preflight("0x1", "v1.2.2", "1.2.3", False, False) == "downgrade_blocked"
    assert flash_preflight("0x1", "v1.1.9", "1.2.0", False, False) == "downgrade_blocked"
    assert flash_preflight("0x1", "v0.9", "1.0.0", False, False) == "downgrade_blocked"
    assert flash_preflight("0x1", "v1.2.2", "1.2.3", True, False) is None  # the downgrade was asked for
    assert flash_preflight("0x1", "v1.2.4", "1.2.3", False, False) is None
    assert flash_preflight("0x1", "v1.2.3", "unreadable", False, False) is None  # an unreadable installed version cannot show a downgrade
    print("preflight of the flash over the real bus: PASS")

    # --- the F-RAM of the kinematic brain: the announcement, the preflight and the operations ------------
    from hydra_suite.can_ota import FRAM_ERASE_WORD, fram_erase_word_matches, hardware_fram_operation, hardware_query_version

    assert flash_preflight("0x1", "v1.2.3", "1.2.3", False, True) == "fram_erase_unsupported"
    assert flash_preflight("0x1", "v1.2.3", "1.2.3", False, True, False, "kinematicBrain") == "fram_erase_unsupported"
    assert flash_preflight("0x1", "v1.2.3", "1.2.3", False, True, True) is None
    assert flash_preflight("0x1", "v1.2.3", "1.2.3", False, True, True, "kinematicBrain") is None
    for other in ("controllerBoard", "urtcHead", "urtcExpansion"):
        assert flash_preflight("0x1", "v1.2.3", "1.2.3", False, True, True, other) == "fram_erase_wrong_tier"
    assert flash_preflight("0x1", "v1.2.3", "1.2.3", False, False, False, "controllerBoard") is None  # no erase asked for: nothing to refuse
    assert flash_preflight(None, "v1.2.3", "1.2.3", False, True, True) == "no_hardware_id"  # the image is checked first
    assert flash_preflight("0x1", "v1.2.2", "1.2.3", False, True, True) == "downgrade_blocked"

    assert FRAM_ERASE_WORD == "ERASE" and fram_erase_word_matches("ERASE") and fram_erase_word_matches("  ERASE ")
    for typed in ("", "erase", "Erase", "ERAS", "ERASEE", "ERASE ME", "E R A S E", None):
        assert not fram_erase_word_matches(typed), typed

    class _Answering:
        def __init__(self, status, body):
            self.status, self.body, self.calls = status, body, []

        async def canota_request(self, method, path, params=None, data=None, json_body=None, timeout=None):
            self.calls.append((method, path, params, data, json_body))
            return self.status, self.body

    version_board = {"online": True, "firmware_major": 0, "firmware_minor": 1, "hardware_id": 1}
    for capabilities, expected in (({"fram_erase": True}, True), ({"fram_erase": False}, False), ({}, False), (None, False), ({"fram_erase": "true"}, False), ({"fram_erase": 1}, False)):
        body = dict(version_board)
        if capabilities is not None:
            body["capabilities"] = capabilities
        queried = asyncio.run(hardware_query_version(_Answering(200, body), CanOtaTarget("Cell", "kinematicBrain")))
        assert queried.online and queried.fram_erase_supported is expected, capabilities

    conn = _Answering(200, {"operation": "erase", "status": "ok", "ok": True, "board_id": 0, "value": 8192})
    done = asyncio.run(hardware_fram_operation(conn, "erase", "ERASE"))
    assert (done.reachable, done.ok, done.status, done.value) == (True, True, "ok", 8192)
    assert conn.calls == [("POST", "/api/hardware/fram/erase", None, None, {"confirm": "ERASE"})]
    for typed in ("", "erase", "ERAS"):
        silent = _Answering(200, {"status": "ok", "ok": True})
        refused = asyncio.run(hardware_fram_operation(silent, "erase", typed))
        assert not refused.ok and silent.calls == [], typed  # an erase never goes out unless the word was typed
    test = _Answering(200, {"operation": "selftest", "status": "ok", "ok": True, "value": 0})
    assert asyncio.run(hardware_fram_operation(test, "selftest")).ok and test.calls[0][4] == {}
    assert not asyncio.run(hardware_fram_operation(test, "format")).ok and len(test.calls) == 1
    for name in ("disabled", "no-chip", "chip-error", "verify-fail"):
        answered = asyncio.run(hardware_fram_operation(_Answering(200, {"status": name, "ok": False, "value": 7}), "erase", "ERASE"))
        assert (answered.reachable, answered.ok, answered.status, answered.value) == (True, False, name, 7)
    assert asyncio.run(hardware_fram_operation(_Answering(403, {"code": "FRAM_ERASE_DISABLED"}), "selftest")).status == "server_disabled"
    assert asyncio.run(hardware_fram_operation(_Answering(503, {"error": "x"}), "selftest")).status == "unreachable"
    assert asyncio.run(hardware_fram_operation(_Answering(504, {"error": "x"}), "selftest")).status == "unreachable"
    assert asyncio.run(hardware_fram_operation(_Answering(500, {}), "selftest")).status == "unknown"
    assert asyncio.run(hardware_fram_operation(_Answering(200, {"status": "ok", "ok": "yes", "value": True}), "selftest")).ok is False
    lost = asyncio.run(hardware_fram_operation(type("Lost", (), {"canota_request": staticmethod(lambda *a, **k: _none())})(), "selftest"))
    assert (lost.reachable, lost.ok, lost.status) == (False, False, "unreachable")
    print("F-RAM operations of the kinematic brain: PASS")

    print("ALL VERIFY_CAN_OTA CHECKS PASSED")


if __name__ == "__main__":
    _run()
