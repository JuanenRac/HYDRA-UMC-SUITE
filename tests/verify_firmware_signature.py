# =============================================================================
# HYDRA-UMC SUITE - tests/verify_firmware_signature.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The Ed25519 check of a firmware image on this computer, before it is sent to the flashing service:
#   - the verifier gives the answers of the RFC 8032 test vector, and refuses a changed message, signature or key
#   - the keys here are made by the test itself (a throwaway seed and a small reference signer written below); no
#     real key is ever read
#   - an image is accepted only with a valid signature for its board, version and bytes; unsigned, tampered, wrong
#     version, wrong board, unknown board and wrong key are refused, each with its own reason
#   - the public key is read from a file named in the configuration (hex with separators, or raw bytes); a missing or
#     damaged file refuses the image; verifying is on unless the configuration says exactly false
#   - the settings page: the path and fingerprint are shown, saving changes only the path, turning the check off asks
#   - the flasher: a refused image never reaches the flashing service; an accepted one does; with the check off the
#     image goes on and the log says so
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import asyncio
import hashlib
import json
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, ".")

import qasync
from PySide6.QtGui import QGuiApplication

from hydra_suite import ed25519_verify, firmware_signature as fs, i18n
from hydra_suite.app import SuiteController
from hydra_suite.i18n import _

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


# --- a small signer for the test (RFC 8032 section 6), only to make throwaway keys ---------------------------------
_P = 2**255 - 19
_Q = 2**252 + 27742317777372353535851937790883648493


def _sign(seed: bytes, message: bytes) -> tuple[bytes, bytes]:
    """(public key, signature) of `message` under a throwaway `seed`, using the arithmetic of the verifier module."""
    ev = ed25519_verify
    digest = hashlib.sha512(seed).digest()
    scalar = (int.from_bytes(digest[:32], "little") & ((1 << 254) - 8)) | (1 << 254)

    def compress(point):
        zinv = ev._inv(point[2])
        x, y = point[0] * zinv % _P, point[1] * zinv % _P
        return int.to_bytes(y | ((x & 1) << 255), 32, "little")

    a_bytes = compress(ev._mul(scalar, ev._BASE))
    r = ev._hash_modq(digest[32:] + message)
    r_bytes = compress(ev._mul(r, ev._BASE))
    h = ev._hash_modq(r_bytes + a_bytes + message)
    return a_bytes, r_bytes + int.to_bytes((r + h * scalar) % _Q, 32, "little")


def _image_message(hardware_id, version, image):
    header = fs.image_header(hardware_id, version, image)
    return fs._IMAGE_DOMAIN + hashlib.sha256(header + image).digest()


# RFC 8032 section 7.1, test 1 (empty message)
RFC_SEED = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
RFC_PUBLIC = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
RFC_SIGNATURE = bytes.fromhex("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")

check("the verifier accepts the RFC 8032 vector", ed25519_verify.verify(RFC_PUBLIC, b"", RFC_SIGNATURE), True)
check("the throwaway signer agrees with the RFC vector", _sign(RFC_SEED, b""), (RFC_PUBLIC, RFC_SIGNATURE))
check("a changed message is refused", ed25519_verify.verify(RFC_PUBLIC, b"x", RFC_SIGNATURE), False)
check("a changed signature is refused", ed25519_verify.verify(RFC_PUBLIC, b"", RFC_SIGNATURE[:-1] + b"\x0c"), False)
check("another key is refused", ed25519_verify.verify(_sign(b"B" * 32, b"")[0], b"", RFC_SIGNATURE), False)
check("wrong lengths are refused", (ed25519_verify.verify(RFC_PUBLIC[:-1], b"", RFC_SIGNATURE), ed25519_verify.verify(RFC_PUBLIC, b"", RFC_SIGNATURE[:-1])), (False, False))

try:  # cross-check with OpenSSL where the package happens to be installed
    from cryptography.hazmat.primitives.asymmetric import ed25519 as _ossl

    key = _ossl.Ed25519PrivateKey.from_private_bytes(b"T" * 32)
    pub = key.public_key().public_bytes_raw()
    check("the same public key and signature as OpenSSL", _sign(b"T" * 32, b"hydra"), (pub, key.sign(b"hydra")))
except ImportError:
    print("skip cross-check with OpenSSL (package not installed)")

# --- images ----------------------------------------------------------------------------------------------------------
SEED = b"throwaway-seed-for-the-test-0001"
HW = 0x47343031
IMAGE = bytes.fromhex("00200020 01900008") + bytes(range(256)) * 4
PUBLIC, SIGNATURE = _sign(SEED, _image_message(HW, (0, 2, 3), IMAGE))
SIG_HEX = SIGNATURE.hex()
OTHER_PUBLIC, OTHER_SIGNATURE = _sign(b"another-throwaway-seed-for-test!", _image_message(HW, (0, 2, 3), IMAGE))

header = fs.image_header(HW, (0, 2, 3), IMAGE)
check("the header is 64 bytes and carries size and CRC of the image", (len(header), header[20:24] == len(IMAGE).to_bytes(4, "little"), header[36:40] == (zlib.crc32(IMAGE) & 0xFFFFFFFF).to_bytes(4, "little")), (64, True, True))
check("an unknown board has no header", fs.image_header(0x12345678, (0, 2, 3), IMAGE), None)


def verdict(image=IMAGE, hw=HW, version="v0.2.3", signature=SIG_HEX, key=PUBLIC):
    v = fs.check_image(image, hw, version, signature, key)
    return v.ok, v.reason


check("a valid signature is accepted", verdict(), (True, "FW_SIG_OK"))
check("a signature with capitals and a newline is accepted", verdict(signature=SIG_HEX.upper() + "\n"), (True, "FW_SIG_OK"))
check("no signature is refused", verdict(signature=None), (False, "FW_SIG_UNSIGNED"))
check("a damaged signature text is refused as unsigned", verdict(signature="abc"), (False, "FW_SIG_UNSIGNED"))
check("a changed byte is refused", verdict(image=IMAGE[:-1] + b"\x00"), (False, "FW_SIG_BAD"))
check("a changed signature is refused", verdict(signature=("0" if SIG_HEX[0] != "0" else "1") + SIG_HEX[1:]), (False, "FW_SIG_BAD"))
check("another version is refused (the header is signed)", verdict(version="v0.2.4"), (False, "FW_SIG_BAD"))
check("another board is refused", verdict(hw=0x48374334), (False, "FW_SIG_BAD"))
check("a signature by another key is refused", verdict(signature=OTHER_SIGNATURE.hex()), (False, "FW_SIG_BAD"))
check("another public key is refused", verdict(key=OTHER_PUBLIC), (False, "FW_SIG_BAD"))
check("an unknown board is refused", verdict(hw=0x12345678), (False, "FW_SIG_NO_HARDWARE"))
check("no board is refused", verdict(hw=None), (False, "FW_SIG_NO_HARDWARE"))
check("an unknown version is refused", verdict(version=None), (False, "FW_SIG_NO_VERSION"))
check("an image too short is refused", verdict(image=b"abc"), (False, "FW_SIG_IMAGE_SHORT"))

# --- the key file and the configuration ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    config_file = root / "hydra_suite_config.json"
    key_file = root / "pub.txt"

    check("the key as hexadecimal with colons", fs.parse_public_key(":".join(PUBLIC.hex()[i:i + 2] for i in range(0, 64, 2)).encode()), PUBLIC)
    check("the key as hexadecimal with a newline", fs.parse_public_key(PUBLIC.hex().encode() + b"\r\n"), PUBLIC)
    check("the key as 32 raw bytes", fs.parse_public_key(PUBLIC), PUBLIC)
    check("a text that is not a key", (fs.parse_public_key(b"hello"), fs.parse_public_key(b"zz" * 32), fs.parse_public_key(PUBLIC.hex().encode()[:-2])), (None, None, None))
    check("the fingerprint is stable and 32 digits", (fs.key_fingerprint(PUBLIC), len(fs.key_fingerprint(PUBLIC).replace(" ", ""))), (" ".join(hashlib.sha256(PUBLIC).hexdigest().upper()[i:i + 4] for i in range(0, 32, 4)), 32))

    default = fs.read_settings({}, config_file)
    check("by default the check is on and the key file sits next to the configuration", (default.verify, default.key_file), (True, root / fs.DEFAULT_KEY_FILE_NAME))
    check("only an exact false turns it off", [fs.read_settings({fs.CONFIG_KEY: {"verify": v}}, config_file).verify for v in (False, 0, "false", None, True, "")], [False, True, True, True, True, True])
    check("a damaged section means the defaults", fs.read_settings({fs.CONFIG_KEY: "oops"}, config_file).verify, True)
    check("the path comes from the configuration", fs.read_settings({fs.CONFIG_KEY: {"publicKeyFile": str(key_file)}}, config_file).key_file, key_file)

    on = fs.SigningSettings(True, key_file)
    off = fs.SigningSettings(False, key_file)
    args = (IMAGE, HW, "v0.2.3", SIG_HEX)
    check("no key file refuses the image", (fs.evaluate(on, *args).ok, fs.evaluate(on, *args).reason), (False, "FW_SIG_NO_KEY"))
    key_file.write_text("not a key")
    check("a damaged key file refuses the image", (fs.evaluate(on, *args).ok, fs.evaluate(on, *args).reason), (False, "FW_SIG_KEY_BAD"))
    key_file.write_text(PUBLIC.hex() + "\n")
    check("a good key and signature are accepted", (fs.evaluate(on, *args).ok, fs.evaluate(on, *args).reason, fs.evaluate(on, *args).skipped), (True, "FW_SIG_OK", False))
    check("an unsigned image is refused with the key in place", fs.evaluate(on, IMAGE, HW, "v0.2.3", None).reason, "FW_SIG_UNSIGNED")
    key_file.write_text(OTHER_PUBLIC.hex())
    check("another key in the file refuses the image", fs.evaluate(on, *args).reason, "FW_SIG_BAD")
    check("with the check off the image goes on, marked as skipped", (fs.evaluate(off, IMAGE, HW, None, None).ok, fs.evaluate(off, IMAGE, HW, None, None).skipped), (True, True))

    # --- the settings page and the flasher -------------------------------------------------------------------------
    i18n.CONFIG_FILE_PATH = config_file  # the real configuration file is never touched
    import qt_suite as qs

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    bridge = qs.SuiteQtBridge(SuiteController())

    view = bridge.firmwareSigningView
    check("page: on by default, default path, no key yet", (view["verify"], view["keyFile"], view["keyOk"], view["fingerprint"], view["warning"]), (True, str(root / fs.DEFAULT_KEY_FILE_NAME), False, "", ""))
    key_file.write_text(PUBLIC.hex())
    bridge.setFirmwareSigningKeyFile(str(key_file))
    view = bridge.firmwareSigningView
    saved = json.loads(config_file.read_text(encoding="utf-8"))
    check("page: saving the path stores only the path", saved[fs.CONFIG_KEY], {"publicKeyFile": str(key_file)})
    check("page: the key and its fingerprint are shown", (view["keyOk"], view["keyStatus"], view["fingerprint"]), (True, _("FW_SIG_KEY_LOADED"), fs.key_fingerprint(PUBLIC)))
    check("page: turning it off asks, turning it on does not", (bridge.firmwareSigningNeedsConfirmation(False), bridge.firmwareSigningNeedsConfirmation(True)), (True, False))

    from hydra_suite.can_ota import CanOtaTarget, HardwareFlashResult

    TARGET = CanOtaTarget(controller_name="bench", tier="kinematicBrain")
    sent = []

    async def fake_start_flash(conn, target, firmware, major, minor, hardware_id=0, signing=None):
        sent.append((len(firmware), signing))
        return HardwareFlashResult(reachable=True, success=True, reason="done")

    qs.hardware_start_flash = fake_start_flash
    qs.resolve_hardware_target = lambda target: object()
    bridge._flasher_is_hardware = True
    bridge._flasher_board_state = lambda key: {}

    class _Controller:
        active_connection = object()

    bridge._controller = _Controller()

    def flash(file):
        bridge._flasher_log["k"] = []
        bridge._flasher_flashing["k"] = False
        sent.clear()
        loop.run_until_complete(bridge._run_flash("k", TARGET, file))
        return [e["text"] for e in bridge._flasher_log["k"]]

    try:
        good = {"name": "app.bin", "bytes": IMAGE, "hardware_id": hex(HW), "version_tag": "v0.2.3", "signature": SIG_HEX}
        log = flash(good)
        check("flasher: a signed image is sent", len(sent), 1)
        check("flasher: the log says the signature was verified", any(_("FW_SIG_OK") in t for t in log), True)
        log = flash({**good, "signature": None})
        check("flasher: an unsigned image is not sent and the reason is logged", (len(sent), any(_("FW_SIG_REFUSED") in t and _("FW_SIG_UNSIGNED") in t for t in log)), (0, True))
        log = flash({**good, "bytes": IMAGE[:-1] + b"\x07"})
        check("flasher: a tampered image is not sent", (len(sent), any(_("FW_SIG_BAD") in t for t in log)), (0, True))
        log = flash({"name": "local.bin", "bytes": IMAGE, "hardware_id": None, "version_tag": None})
        check("flasher: a file picked from disk (no board, version or signature) is not sent", len(sent), 0)
        bridge.setFirmwareSigningVerify(False)
        check("page: off shows the warning", bridge.firmwareSigningView["warning"], _("FW_SIG_WARNING_OFF"))
        log = flash({**good, "signature": None})
        check("flasher: with the check off the image is sent and the log warns", (len(sent), any(_("FW_SIG_OFF_LOG") in t for t in log)), (1, True))
        bridge.setFirmwareSigningVerify(True)
        check("page: on again, the warning goes", (bridge.firmwareSigningView["verify"], bridge.firmwareSigningView["warning"]), (True, ""))
    finally:
        loop.close()

print("FAILED" if failures else "PASS", failures)
sys.exit(1 if failures else 0)
