# =============================================================================
# HYDRA-UMC SUITE - hydra_suite/firmware_signature.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Checks the Ed25519 signature of a firmware image on this computer, before the image is sent to the flashing service.

The bootloader of every board verifies the signature again; this check only keeps an unsigned or tampered image from
travelling to the service and the board at all, and tells the person why. The signature covers the 64-byte image header
(rebuilt here from the hardware id, the version and the image itself) followed by the image, under a domain tag.

The public key is read from a file whose path is in the configuration of the program (`firmwareSignature` in
`hydra_suite_config.json`, editable by hand or from the settings page):

    "firmwareSignature": {"verify": true, "publicKeyFile": "C:/path/to/firmware_public_key.txt"}

The file holds the 32-byte key as 64 hexadecimal digits (spaces and colons are ignored) or as 32 raw bytes. Nothing but the
path is stored in the configuration. Verifying is on by default; with it off the image goes unchecked (the bootloader still
checks it) and the settings page says so. With it on, every failure - no key, a damaged key, no signature, a bad one, an
unknown board - refuses the image (fail closed).
"""
from __future__ import annotations

import hashlib
import re
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

from hydra_suite import ed25519_verify
from hydra_suite.can_ota import normalize_signature, parse_version_full

CONFIG_KEY = "firmwareSignature"
DEFAULT_KEY_FILE_NAME = "firmware_public_key.txt"

_MAGIC = 0x52445948
_FORMAT = 1
_HEADER = struct.Struct("<IHHIHHHHIIIII24s")
_IMAGE_DOMAIN = b"hydra-umc-image-sig\x00"

# Where each bootloader runs its application image (the same table the signing tool uses).
LINK_ADDRESS_BY_HARDWARE_ID = {
    0x47343031: 0x08009000,  # G401
    0x48374334: 0x08140000,  # H7C4
    0x48374337: 0x08040000,  # H7C7
}


@dataclass(frozen=True)
class SigningSettings:
    verify: bool
    key_file: Path


@dataclass(frozen=True)
class Verdict:
    """`ok` lets the image go on. `reason` is a language key (FW_SIG_*); `skipped` is True when verifying is off."""

    ok: bool
    reason: str
    skipped: bool = False


def default_key_file(config_file: Path) -> Path:
    return config_file.parent / DEFAULT_KEY_FILE_NAME


def read_settings(config: dict, config_file: Path) -> SigningSettings:
    """The settings in `config`; verifying is on unless the file says exactly `false`, and a missing path means the default one."""
    section = config.get(CONFIG_KEY)
    if not isinstance(section, dict):
        section = {}
    verify = section.get("verify") is not False
    raw = section.get("publicKeyFile")
    key_file = Path(raw.strip()).expanduser() if isinstance(raw, str) and raw.strip() else default_key_file(config_file)
    return SigningSettings(verify, key_file)


def parse_public_key(data: bytes) -> bytes | None:
    """The 32-byte key in `data` (64 hexadecimal digits, with or without separators, or 32 raw bytes); None when it is neither."""
    if len(data) == 32:
        return bytes(data)
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        return None
    clean = re.sub(r"[\s:]", "", text).lower()
    return bytes.fromhex(clean) if re.fullmatch(r"[0-9a-f]{64}", clean) else None


def load_public_key(path: Path) -> tuple[bytes | None, str]:
    """(key, "") or (None, reason) where reason is FW_SIG_NO_KEY (no file) or FW_SIG_KEY_BAD (unreadable or not a key)."""
    try:
        data = path.read_bytes()
    except OSError:
        return None, "FW_SIG_NO_KEY"
    key = parse_public_key(data)
    return (key, "") if key is not None else (None, "FW_SIG_KEY_BAD")


def key_fingerprint(public_key: bytes) -> str:
    """SHA-256 of the key as uppercase hexadecimal in groups of four, first 128 bits: what the person compares with the signer's."""
    digest = hashlib.sha256(public_key).hexdigest().upper()[:32]
    return " ".join(digest[i:i + 4] for i in range(0, 32, 4))


def image_header(hardware_id: int, version: tuple[int, int, int], image: bytes) -> bytes | None:
    """The 64-byte header of `image`, as the signing tool builds it; None for a board without a known link address or an image too short."""
    link = LINK_ADDRESS_BY_HARDWARE_ID.get(hardware_id)
    if link is None or len(image) < 8:
        return None
    sp, reset = struct.unpack_from("<II", image, 0)
    return _HEADER.pack(_MAGIC, _FORMAT, 0, hardware_id, version[0], version[1], version[2], 0,
                        len(image), link, sp, reset, zlib.crc32(image) & 0xFFFFFFFF, b"\x00" * 24)


def check_image(image: bytes, hardware_id: int | None, version_tag: str | None, signature: str | None, public_key: bytes) -> Verdict:
    """Whether `signature` is the valid signature, under `public_key`, of this image for this board and version."""
    sig_hex = normalize_signature(signature)
    if sig_hex is None:
        return Verdict(False, "FW_SIG_UNSIGNED")
    version = parse_version_full(version_tag)
    if version is None:
        return Verdict(False, "FW_SIG_NO_VERSION")
    if hardware_id is None or hardware_id not in LINK_ADDRESS_BY_HARDWARE_ID:
        return Verdict(False, "FW_SIG_NO_HARDWARE")
    header = image_header(hardware_id, version, image)
    if header is None:
        return Verdict(False, "FW_SIG_IMAGE_SHORT")
    message = _IMAGE_DOMAIN + hashlib.sha256(header + image).digest()
    if ed25519_verify.verify(public_key, message, bytes.fromhex(sig_hex)):
        return Verdict(True, "FW_SIG_OK")
    return Verdict(False, "FW_SIG_BAD")


def evaluate(settings: SigningSettings, image: bytes, hardware_id: int | None, version_tag: str | None, signature: str | None) -> Verdict:
    """The decision before an image is sent: verifying off lets it go (skipped); otherwise only a valid signature does."""
    if not settings.verify:
        return Verdict(True, "FW_SIG_OFF", skipped=True)
    key, problem = load_public_key(settings.key_file)
    if key is None:
        return Verdict(False, problem)
    return check_image(image, hardware_id, version_tag, signature, key)
