"""Real assertion-based coverage for can_ota.py - the SUITE-side port of
HYDRA-UMC-STUDIO's own src/lib/canOta.ts. Covers the pure
helpers, the mock async generators (mock_flash/mock_self_test - run for
real, not stubbed, since they're fast enough headless), CRC32 against a
known real value, and resolve_hardware_target's own real tier-mapping
boundary (Tier 3 stays unreachable on purpose)."""
import asyncio
import sys

sys.path.insert(0, ".")
from hydra_suite.can_ota import (
    CanOtaTarget,
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


def _run() -> None:
    # --- pure helpers --------------------------------------------------
    assert slot_label(0) == "A1"
    assert slot_label(7) == "A8"
    assert slot_base_id(0) == 0x600
    assert slot_base_id(1) == 0x620

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

    print("ALL VERIFY_CAN_OTA CHECKS PASSED")


if __name__ == "__main__":
    _run()
