# =============================================================================
# HYDRA-UMC SUITE - diagnostics.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# A support bundle: one zip with the versions of everything this machine runs,
# the servers the window knows about and the client log the Logs panel keeps.
# It is meant to be attached to a report, so nothing secret goes in: server
# entries carry only host, port and public facts (never the user name, the
# password or a token) and the log text is scrubbed of anything that looks like
# a credential before it is written. No Qt is needed here.
# =============================================================================
from __future__ import annotations

import io
import platform
import re
import sys
import zipfile
from typing import Iterable, Sequence

from hydra_suite import __version__

REDACTED = "[hidden]"
# key=value, key: value and "key": "value" forms for names that carry secrets,
# and a bearer / JWT-looking value on its own.
_SECRET_NAMES = r"(?:password|passwd|pass|token|refreshtoken|refresh_token|secret|authorization|api[_-]?key)"
_PAIR = re.compile(rf"(?i)(\"?{_SECRET_NAMES}\"?\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;&}}]+)")
_BEARER = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*")
_URL_TOKEN = re.compile(r"(?i)([?&#](?:token|access_token|refresh_token)=)[^&\s]+")


def redact(text: str) -> str:
    """The text with credentials replaced by a marker."""
    text = _BEARER.sub(lambda m: m.group(1) + REDACTED, text)
    text = _PAIR.sub(lambda m: m.group(1) + REDACTED, text)
    text = _URL_TOKEN.sub(lambda m: m.group(1) + REDACTED, text)
    return _JWT.sub(REDACTED, text)


def _qt_versions() -> str:
    try:
        import PySide6
        from PySide6.QtCore import qVersion

        return f"PySide6 {PySide6.__version__} / Qt {qVersion()}"
    except Exception:  # noqa: BLE001 - a diagnostic must never fail because of a missing part
        return "PySide6 unavailable"


def system_summary() -> str:
    lines = [
        f"HYDRA-UMC SUITE: {__version__}",
        f"Python: {platform.python_version()} ({platform.python_implementation()})",
        f"Platform: {platform.platform()}",
        f"Frozen build: {'yes' if getattr(sys, 'frozen', False) else 'no'}",
        f"Qt: {_qt_versions()}",
    ]
    return "\n".join(lines)


def describe_servers(servers: Iterable[dict]) -> str:
    """One block per server. Only the listed public fields are written, so a
    credential kept in the entry can never reach the bundle."""
    fields = ("label", "host", "port", "status", "app_version", "remote_api_version", "role")
    blocks = []
    for index, server in enumerate(servers, start=1):
        rows = [f"  {name}: {server[name]}" for name in fields if server.get(name) not in (None, "")]
        blocks.append(f"Server {index}\n" + "\n".join(rows))
    return "\n\n".join(blocks) if blocks else "No server in the list."


def build_report(servers: Iterable[dict]) -> str:
    return f"{system_summary()}\n\n{describe_servers(servers)}\n"


def build_bundle(servers: Iterable[dict], log_lines: Sequence[str]) -> bytes:
    """The zip as bytes: report.txt and client_log.txt."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("report.txt", redact(build_report(servers)))
        archive.writestr("client_log.txt", redact("\n".join(log_lines)) + "\n")
    return buffer.getvalue()
