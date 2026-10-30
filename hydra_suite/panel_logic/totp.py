# =============================================================================
# HYDRA-UMC SUITE - panel_logic/totp.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The second factor of the sign-in, without any window toolkit: reading the answers of the server routes
# /api/totp/status|begin|confirm|disable defensively, the sentence for each refusal, and the key and the code as they are
# shown and typed. Nothing here stores a secret: the key and the recovery codes live only in the screen that shows them.
# =============================================================================
from __future__ import annotations

import re

from hydra_suite.i18n import _
from hydra_suite.panel_logic.qr_code import encode_qr, qr_svg_path

_KEY = re.compile(r"^[A-Z2-7]{16,128}$")
_RECOVERY = re.compile(r"^[0-9a-f]{5}-[0-9a-f]{5}$")


def parse_status(body: object) -> tuple[bool, int] | None:
    """(enabled, recovery codes left) from GET /api/totp/status, or None when the answer is not that."""
    if not isinstance(body, dict) or not isinstance(body.get("enabled"), bool):
        return None
    left = body.get("recoveryLeft")
    return body["enabled"], left if isinstance(left, int) and not isinstance(left, bool) and left >= 0 else 0


def parse_enrolment(body: object) -> tuple[str, str] | None:
    """(key, otpauth address) from POST /api/totp/begin; anything that is not a base32 key and an otpauth address is refused."""
    if not isinstance(body, dict):
        return None
    secret, uri = body.get("secret"), body.get("uri")
    if not isinstance(secret, str) or not _KEY.match(secret):
        return None
    if not isinstance(uri, str) or not uri.startswith("otpauth://totp/"):
        return None
    return secret, uri


def parse_recovery_codes(body: object) -> list[str] | None:
    """The one-time recovery codes of POST /api/totp/confirm; None unless every one has the shape the server makes."""
    codes = body.get("recoveryCodes") if isinstance(body, dict) else None
    if not isinstance(codes, list) or not codes:
        return None
    if not all(isinstance(code, str) and _RECOVERY.match(code) for code in codes):
        return None
    return list(codes)


def grouped_key(secret: str) -> str:
    """The key in groups of four letters, easier to type from the screen."""
    return " ".join(secret[i:i + 4] for i in range(0, len(secret), 4))


def normalize_code(text: str) -> str:
    """An app code stays six digits however it was spaced; a recovery code is kept as typed, in lower case."""
    trimmed = text.strip()
    digits = re.sub(r"[\s-]", "", trimmed)
    return digits if re.fullmatch(r"\d{6}", digits) else trimmed.lower()


def failure_text(status: int, body: object = None, retry_after: str | None = None, password_call: bool = True) -> str:
    """The sentence for a refused or failed call. `password_call` says whether the call also sends the password, so a
    401 without totpRequired is the password (and, when turning it off, a message that names the code is the code)."""
    data = body if isinstance(body, dict) else {}
    if status == 0:
        return _("TOTP_ERR_NETWORK")
    if status == 404:
        return _("TOTP_ERR_UNSUPPORTED")
    if status == 403:
        return _("TOTP_ERR_FORBIDDEN")
    if status == 409:
        return _("TOTP_ERR_ALREADY")
    if status == 429:
        try:
            seconds = int(float(retry_after)) if retry_after is not None else 30
        except ValueError:
            seconds = 30
        return _("TOTP_ERR_WAIT", seconds=seconds if seconds > 0 else 30)
    if status == 401:
        detail = str(data.get("error", ""))
        if data.get("totpRequired") is True or "code" in detail.lower() or not password_call:
            return _("TOTP_ERR_CODE")
        return _("TOTP_ERR_PASSWORD")
    if status == 400:
        return _("TOTP_ERR_CODE")
    return _("TOTP_ERR_HTTP", status=status)


def qr_view(uri: str) -> dict[str, object]:
    """What the screen draws for the otpauth address: the path of the symbol and its side, or `tooLong` when it does not fit."""
    matrix = encode_qr(uri)
    if matrix is None:
        return {"tooLong": True, "path": "", "size": 0, "modules": []}
    path, size = qr_svg_path(matrix)
    # The rows as strings of 0 and 1, the cheapest shape for the Qt Quick canvas to draw.
    return {"tooLong": False, "path": path, "size": size, "modules": ["".join(str(v) for v in row) for row in matrix]}
