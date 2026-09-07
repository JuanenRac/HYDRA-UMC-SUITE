# =============================================================================
# HYDRA-UMC SUITE - can_ota.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real port of HYDRA-UMC-STUDIO's own src/lib/canOta.ts (510 lines) - the
# shared CAN-OTA (and, for the Kinematic Brain, SPI-OTA) transport used by
# both flasher_panel.py and tester_panel.py, mirroring how Flasher.tsx/
# Tester.tsx both import from the one canOta.ts module rather than each
# having their own copy.
#
# Client-side model of the 4-tier chain documented in HYDRA-UMC's own
# docs/architecture.md: this app -> SPI -> STM32H745ZIT6 "kinematic brain"
# (Tier 0) -> FDCAN1 "STACK A" -> that robot's own STM32G474RET6 Robot
# Controller Board (Tier 1, one of up to 8 slots, A1-A8) -> CAN (relay) ->
# its STM32F303CCT6 URTC Tool Head (Tier 2) -> I2C (relay) -> its optional
# STM32F303CBT6 Advanced Expansion Board (Tier 3, only present when that
# URTC head's own expansion_board_type is 3 or 4).
#
# TRANSPORT: 'mock' simulates realistic timing/behavior entirely
# client-side - still the only path for urtcHead/urtcExpansion (Tier 2-3),
# which have no real relay tunnel yet. 'hardware' now reaches a REAL path
# for kinematicBrain/controllerBoard (Tier 0-1) via HYDRA-UMC-SERVER's own
# /api/hardware/canota/* routes - see HydraConnection.canota_request()
# (net/client.py). No populated STM32H745 board exists yet to actually
# verify this against - the software path is real and tested, the
# hardware on the other end isn't yet, same honest boundary as STUDIO's
# own source. CRC32 itself is computed for real (zlib.crc32 - same IEEE
# 802.3 polynomial STUDIO's own hand-rolled table produces) regardless of
# which transport ends up sending it.
# =============================================================================
from __future__ import annotations

import asyncio
import random
import time
import zlib
from dataclasses import dataclass, field
from typing import AsyncGenerator, Literal

import httpx

CanOtaTier = Literal["kinematicBrain", "controllerBoard", "urtcHead", "urtcExpansion"]
FlashPhase = Literal[
    "connecting", "entering_bootloader", "erasing_fram", "transferring", "verifying", "rebooting", "done", "error"
]

TIERS: tuple[CanOtaTier, ...] = ("kinematicBrain", "controllerBoard", "urtcHead", "urtcExpansion")


@dataclass
class CanOtaTarget:
    controller_name: str
    tier: CanOtaTier
    # Unused (None) for 'kinematicBrain' - that tier is controller-level,
    # reached directly over SPI, no FDCAN1 "STACK A" slot involved.
    robot_id: int | None = None
    robot_name: str | None = None
    robot_index0: int | None = None  # 0-7, position within its controller's robots[] array


def slot_label(robot_index0: int) -> str:
    """"A1".."A8" - matches the default robot naming and HYDRA-UMC's own STACK A slot labels."""
    return f"A{robot_index0 + 1}"


def slot_base_id(robot_index0: int) -> int:
    """CAN_ID_STACKA_BASE + slot*0x20 - see architecture.md section 3."""
    return 0x600 + robot_index0 * 0x20


def tier_base_id(robot_index0: int, _tier: CanOtaTier) -> int:
    """Robot Controller Board's own bootloader/telemetry block, +0x00 within its slot."""
    return slot_base_id(robot_index0)


def hop_count(tier: CanOtaTier) -> int:
    """Number of relay hops a target is reached through - drives simulated latency and the hop description."""
    return {"kinematicBrain": 0, "controllerBoard": 1, "urtcHead": 2, "urtcExpansion": 3}[tier]


def hop_description(target: CanOtaTarget) -> str:
    if target.tier == "kinematicBrain":
        return f"{target.controller_name} -> SPI -> STM32H745ZIT6 (Kinematic Brain)"
    base = f"{target.controller_name} -> SPI -> STM32H745 -> FDCAN1 (STACK A) -> {slot_label(target.robot_index0)} (STM32G474RET6)"
    if target.tier == "controllerBoard":
        return base
    if target.tier == "urtcHead":
        return f"{base} -> CAN (relay) -> URTC Tool Head (STM32F303CCT6)"
    return f"{base} -> CAN (relay) -> URTC Tool Head -> I2C (relay) -> Advanced Expansion (STM32F303CBT6)"


def chip_name_for(tier: CanOtaTier) -> str:
    return {
        "kinematicBrain": "STM32H745ZIT6",
        "controllerBoard": "STM32G474RET6",
        "urtcHead": "STM32F303CCT6",
        "urtcExpansion": "STM32F303CBT6",
    }[tier]


def has_advanced_expansion(expansion_board_type: int | None) -> bool:
    """expansion_board_type values 3 (TMC2209) and 4 (TMC5160A) are the 2
    "Advanced" variants with their own STM32F303CBT6 - see
    URTC/docs/EXPANSION.TXT section 2-3. Everything else has no separate
    MCU to flash."""
    return expansion_board_type in (3, 4)


def crc32(data: bytes) -> int:
    """Real CRC32 (IEEE 802.3 polynomial) via zlib - same algorithm
    STUDIO's own hand-rolled CRC32_TABLE computes, no need to reimplement
    the table here."""
    return zlib.crc32(data) & 0xFFFFFFFF


def _hop_latency_s(target: CanOtaTarget) -> float:
    """Simulated per-hop latency, in seconds - each relay tier crosses one
    more physical bus than the last, so it should visibly take a little
    longer in the mock too. (STUDIO's own hopLatencyMs is milliseconds;
    kept as seconds here since asyncio.sleep() takes seconds.)"""
    return (15 + hop_count(target.tier) * 15) / 1000.0


@dataclass
class VersionQueryResult:
    online: bool
    firmware_version: str | None = None
    bootloader_version: str | None = None
    hardware_id: str | None = None
    expansion_board_type: int | None = None  # only meaningful for a urtcHead query


async def mock_query_version(target: CanOtaTarget) -> VersionQueryResult:
    """Simulates the VERSION_QUERY/VERSION_RESPONSE round trip (mirrors
    URTC's own 0x7F8/0x7F9/0x7FA)."""
    await asyncio.sleep(_hop_latency_s(target) * 2)
    # ~90% of the time a target that's plausibly online answers - purely
    # cosmetic randomness so the UI has something realistic to show
    # without a real bus to query.
    if random.random() <= 0.05:
        return VersionQueryResult(online=False)
    prefix = {"kinematicBrain": "KB", "controllerBoard": "RCB", "urtcHead": "URTC", "urtcExpansion": "EXP"}[target.tier]
    return VersionQueryResult(
        online=True,
        firmware_version=f"0.{random.randint(0, 3)}.{random.randint(0, 9)}",
        bootloader_version="0.0.0",
        hardware_id=f"{prefix}-{((target.robot_index0 or -1) + 1):03d}",
        expansion_board_type=random.choice([0, 0, 0, 3, 6]) if target.tier == "urtcHead" else None,
    )


@dataclass
class FlashProgress:
    phase: FlashPhase
    pages_sent: int
    pages_total: int
    percent: int
    message_key: str  # i18n key under flasher.progress.*
    error: str | None = None


FLASH_PAGE_SIZE = 2048  # matches URTC's own bootloader page size


@dataclass
class FlashOptions:
    allow_downgrade: bool
    erase_fram: bool


async def mock_flash(target: CanOtaTarget, firmware: bytes, opts: FlashOptions) -> AsyncGenerator[FlashProgress, None]:
    """Simulates a full CAN-OTA (or, for kinematicBrain, SPI-OTA) flash
    cycle: ENTER_BOOTLOADER -> (optional FRAM erase) -> START_UPDATE ->
    page-by-page DATA+PAGE_ACK -> END_UPDATE (CRC32+version) ->
    STATUS/HEARTBEAT verify -> reboot to app. Mirrors URTC's own
    bootloader state machine, relayed 0-3 extra hops depending on target
    tier."""
    latency = _hop_latency_s(target)
    pages_total = max(1, -(-len(firmware) // FLASH_PAGE_SIZE))  # ceil division

    yield FlashProgress("connecting", 0, pages_total, 0, "connecting")
    await asyncio.sleep(latency * 3)

    yield FlashProgress("entering_bootloader", 0, pages_total, 2, "entering_bootloader")
    await asyncio.sleep(latency * 2)

    if opts.erase_fram:
        yield FlashProgress("erasing_fram", 0, pages_total, 4, "erasing_fram")
        await asyncio.sleep(latency * 2)

    for page in range(1, pages_total + 1):
        await asyncio.sleep(latency + random.random() * latency * 0.5)
        percent = 5 + round((page / pages_total) * 80)
        yield FlashProgress("transferring", page, pages_total, percent, "transferring")

    yield FlashProgress("verifying", pages_total, pages_total, 90, "verifying")
    await asyncio.sleep(latency * 4)

    # Anti-rollback simulation: only meaningful cosmetically here (no real
    # installed-version bookkeeping in the mock), included so the
    # option's effect is visibly represented.
    if not opts.allow_downgrade and random.random() < 0.03:
        yield FlashProgress("error", pages_total, pages_total, 90, "error_rollback", error="anti-rollback")
        return

    yield FlashProgress("rebooting", pages_total, pages_total, 96, "rebooting")
    await asyncio.sleep(latency * 3)

    yield FlashProgress("done", pages_total, pages_total, 100, "done")


@dataclass
class SelfTestStep:
    id: str
    label_key: str  # i18n key under tester.selftest.*
    passed: bool
    detail: str | None = None


async def mock_self_test(target: CanOtaTarget) -> AsyncGenerator[SelfTestStep, None]:
    """Safe, at-rest checks only - mirrors URTC-TESTER's own explicit
    philosophy: confirms comms and, where relevant, a zero setpoint
    round-trips, never actuates anything at meaningful power. Steps vary
    by tier."""
    latency = _hop_latency_s(target)
    steps: list[tuple[str, str]] = [("comm", "comm"), ("version", "version")]
    if target.tier == "kinematicBrain":
        steps += [("spi", "spi"), ("fdcan", "fdcan")]
    if target.tier == "controllerBoard":
        steps += [("fram", "fram"), ("axes", "axes"), ("endstops", "endstops")]
    if target.tier == "urtcHead":
        steps += [("fram", "fram"), ("tool", "tool"), ("telemetry", "telemetry")]
    if target.tier == "urtcExpansion":
        steps += [("i2c", "i2c"), ("telemetry", "telemetry")]

    for step_id, label_key in steps:
        await asyncio.sleep(latency * 2 + random.random() * latency)
        yield SelfTestStep(id=step_id, label_key=label_key, passed=random.random() > 0.05)


@dataclass
class CanFrame:
    id: int
    dlc: int
    data: list[int]
    direction: Literal["tx", "rx"]
    timestamp: float


async def mock_bus_monitor(target: CanOtaTarget) -> AsyncGenerator[CanFrame, None]:
    """Emits periodic heartbeat/telemetry-shaped frames for the Raw Bus
    Monitor - an async generator here (the caller cancels the task to
    stop, matching the stop-function STUDIO's own startMockBusMonitor()
    returns) rather than a callback-based API, the more natural shape for
    an asyncio consumer."""
    base = 0x000 if target.tier == "kinematicBrain" else tier_base_id(target.robot_index0, target.tier)
    await asyncio.sleep(0.2)
    while True:
        is_heartbeat = random.random() > 0.4
        dlc = 2 if is_heartbeat else 4
        yield CanFrame(
            id=base + (0x06 if is_heartbeat else 0x08),
            dlc=dlc,
            data=[random.randint(0, 255) for _ in range(dlc)],
            direction="rx",
            timestamp=time.time(),
        )
        await asyncio.sleep(_hop_latency_s(target) * 8 + random.random() * 0.4)


# ---------------------------------------------------------------------------
# GitHub firmware download - lets the Flasher pick a firmware asset
# straight from a project's own repo instead of browsing for a local .bin.
# Reads `{MANIFEST_DIR}/firmware_manifest.json` from a repo's own default
# branch (raw.githubusercontent.com - no auth needed for a public repo) -
# see canOta.ts's own header comment for the real history behind why this
# reads a manifest, not the GitHub Releases API.
# ---------------------------------------------------------------------------

GITHUB_FIRMWARE_REPO: dict[CanOtaTier, str] = {
    "kinematicBrain": "JuanenRac/HYDRA-UMC",
    "controllerBoard": "JuanenRac/HYDRA-UMC",
    "urtcHead": "JuanenRac/URTC",
    "urtcExpansion": "JuanenRac/URTC",
}

MANIFEST_DIR: dict[str, str] = {
    "JuanenRac/URTC": "firmware",
    "JuanenRac/HYDRA-UMC": "firmware",
}

TIER_COMPONENTS: dict[CanOtaTier, list[str]] = {
    "kinematicBrain": ["h745_cm7_bootloader", "h745_cm7_application", "h745_cm4_bootloader", "h745_cm4_application"],
    "controllerBoard": ["g474_bootloader", "g474_application"],
    "urtcHead": ["main_bootloader", "main_application"],
    "urtcExpansion": ["slave_bootloader", "slave_application"],
}


@dataclass
class GithubFirmwareAsset:
    name: str
    url: str
    size: int
    release_tag: str  # "version string from the manifest" (e.g. "1.2.0")
    published_at: str
    crc32: str | None = None
    display_name: str | None = None
    chip: str | None = None
    hardware_id: str | None = None  # real hardware_id (e.g. "0x48374334") the bootloader validates START_UPDATE against


async def fetch_github_firmware_releases(repo: str, tier: CanOtaTier, branch: str = "main") -> list[GithubFirmwareAsset]:
    directory = MANIFEST_DIR.get(repo)
    if not directory:
        raise ValueError(f"No known firmware_manifest.json location for {repo}")
    manifest_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{directory}/firmware_manifest.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(manifest_url, timeout=10.0)
    if resp.status_code != 200:
        if resp.status_code == 404:
            # Real, expected state until the repo owner actually commits+pushes
            # a build's own output - not a bug, so this returns an empty list.
            return []
        raise RuntimeError(f"GitHub raw content {resp.status_code} fetching {manifest_url}")
    manifest = resp.json()
    components = manifest.get("components", {})
    keys = TIER_COMPONENTS.get(tier, [])
    assets: list[GithubFirmwareAsset] = []
    for key in keys:
        comp = components.get(key)
        if not comp:
            continue
        bin_info = comp["files"]["bin"]
        assets.append(
            GithubFirmwareAsset(
                name=bin_info["filename"],
                url=f"https://raw.githubusercontent.com/{repo}/{branch}/{directory}/{bin_info['filename']}",
                size=bin_info["size_bytes"],
                release_tag=comp["version_string"],
                published_at="",
                crc32=bin_info.get("crc32"),
                display_name=comp.get("display_name"),
                chip=comp.get("chip"),
                hardware_id=comp.get("hardware_id"),
            )
        )
    return assets


async def download_github_firmware(asset: GithubFirmwareAsset) -> bytes:
    async with httpx.AsyncClient() as client:
        resp = await client.get(asset.url, timeout=30.0)
    if resp.status_code != 200:
        raise RuntimeError(f"Download failed: {resp.status_code}")
    data = resp.content
    if asset.crc32:
        actual = f"0x{crc32(data):08X}"
        if actual != asset.crc32:
            raise RuntimeError(f"CRC32 mismatch after download: manifest says {asset.crc32}, got {actual} - file changed or download corrupted, not flashing this.")
    return data


# ---------------------------------------------------------------------------
# REAL hardware transport - HYDRA-UMC-SERVER's own
# /api/hardware/canota/{version,flash} relay to HYDRA-UMC's
# src/cm5_host/spi_bridge/ local service, itself the real SPI1 +
# HYDRA_DATA_READY GPIO link to the STM32H745. `transport == 'hardware'`
# reaches this real path - see flasher_panel.py/tester_panel.py for where
# the switch is read.
# ---------------------------------------------------------------------------

SPI_TARGET_SELF = 0
SPI_TARGET_CM7 = 1
SPI_TARGET_STACKA = 2


@dataclass
class HardwareTargetResolution:
    target_tier: int
    target_slot: int
    relay: bool  # true for urtcHead - tunnel through the resolved Tier 1 target instead of talking to it directly


def resolve_hardware_target(target: CanOtaTarget) -> HardwareTargetResolution | None:
    """Maps the 4-tier logical CanOtaTier onto the real spi_bridge target
    it's actually reached through. Returns None only for urtcExpansion -
    not a bug, a real, honest boundary: Tier 3 needs one further real
    tunnel hop (URTC's own I2C bridge) that doesn't exist yet."""
    if target.tier == "kinematicBrain":
        return HardwareTargetResolution(SPI_TARGET_SELF, 0, False)
    if target.tier == "controllerBoard":
        return HardwareTargetResolution(SPI_TARGET_STACKA, target.robot_index0 or 0, False)
    if target.tier == "urtcHead":
        return HardwareTargetResolution(SPI_TARGET_STACKA, target.robot_index0 or 0, True)
    return None


async def hardware_query_version(conn, target: CanOtaTarget) -> VersionQueryResult:
    """Real GET /api/hardware/canota/version via the given HydraConnection
    (net/client.py) - same VersionQueryResult shape mock_query_version()
    returns, so flasher_panel.py/tester_panel.py don't need a separate
    result type for the hardware path."""
    resolved = resolve_hardware_target(target)
    if not resolved:
        return VersionQueryResult(online=False)
    result = await conn.canota_request(
        "GET", "/api/hardware/canota/version",
        params={"tier": resolved.target_tier, "slot": resolved.target_slot, "relay": "1" if resolved.relay else "0"},
    )
    if result is None:
        return VersionQueryResult(online=False)
    status, body = result
    if status != 200 or not isinstance(body, dict) or not body.get("online"):
        return VersionQueryResult(online=False)
    return VersionQueryResult(
        online=True,
        firmware_version=f"{body.get('firmware_major', 0)}.{body.get('firmware_minor', 0)}.0",
        hardware_id=f"0x{int(body.get('hardware_id', 0)):08X}",
    )


@dataclass
class HardwareFlashResult:
    reachable: bool
    success: bool
    reason: str


async def hardware_start_flash(
    conn, target: CanOtaTarget, firmware: bytes, version_major: int, version_minor: int, hardware_id: int = 0
) -> HardwareFlashResult:
    """Real POST /api/hardware/canota/flash. Unlike mock_flash(), this is
    NOT an async generator - the real per-page progress arrives over the
    WebSocket ("canota_progress" broadcast), not this HTTP response,
    which only ever reports the final outcome once the whole cycle ends.
    The caller watches the connection's own live state for progress
    while this coroutine is pending.

    `hardware_id` should come from the real firmware_manifest.json entry
    for the file being flashed (GithubFirmwareAsset.hardware_id) when
    known - a locally browsed .bin with no manifest metadata has no real
    hardware_id to send, so this defaults to 0 and lets the real
    bootloader reject it rather than this app guessing one."""
    resolved = resolve_hardware_target(target)
    if not resolved:
        return HardwareFlashResult(
            reachable=False, success=False,
            reason="not reachable over hardware yet - Tier 3 needs a real I2C-bridge tunnel hop that does not exist yet",
        )
    params = {
        "tier": resolved.target_tier,
        "slot": resolved.target_slot,
        "relay": "1" if resolved.relay else "0",
        "hardware_id": hardware_id,
        "version_major": version_major,
        "version_minor": version_minor,
    }
    result = await conn.canota_request("POST", "/api/hardware/canota/flash", params=params, data=firmware)
    if result is None:
        return HardwareFlashResult(reachable=True, success=False, reason="network error")
    status, body = result
    if not isinstance(body, dict):
        body = {}
    if status < 200 or status >= 300:
        return HardwareFlashResult(reachable=True, success=False, reason=body.get("error", f"HTTP {status}"))
    return HardwareFlashResult(reachable=True, success=bool(body.get("success")), reason=body.get("finalPhase", "unknown"))
