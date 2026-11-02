# =============================================================================
# HYDRA-UMC SUITE - update_check.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The check of versions, the same one HYDRA-UMC-UPDATER makes: the version of a project is the `version` of the
# `hydra-umc.project.json` that sits in its repository, read from the raw content of GitHub. This program compares
#   - its own version with the newest one of HYDRA-UMC-SUITE,
#   - the version each connected server reports (`appVersion`) with the newest one of HYDRA-UMC-SERVER,
#   - the `remoteApiVersion` each server reports with the lowest one this program works with.
# Nothing is installed here: the answer says what is behind, and installing is the job of HYDRA-UMC-UPDATER.
# The check reaches out to the Internet, so it runs only when the operator presses the button and only after the
# switch is on (off until switched on). The addresses and the lowest API version are in assets/update_check.json.
# A version is MAJOR.MINOR.PATCH with an optional fourth number (0.8.0 equals 0.8.0.0), as in the UPDATER.
# =============================================================================
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterable

CONFIG_PATH = Path(__file__).resolve().parent.parent / "assets" / "update_check.json"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:\.\d+)?$")
ECOSYSTEM_ID = "HYDRA-UMC"

_FALLBACK: dict[str, Any] = {
    "enabledByDefault": False,
    "owner": "JuanenRac",
    "branch": "main",
    "manifestFile": "hydra-umc.project.json",
    "rawBase": "https://raw.githubusercontent.com",
    "suiteRepository": "HYDRA-UMC-SUITE",
    "serverRepository": "HYDRA-UMC-SERVER",
    "timeoutSeconds": 8,
    "minRemoteApiVersion": 2,
}


def load_settings(path: Path = CONFIG_PATH) -> dict[str, Any]:
    merged = dict(_FALLBACK)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return merged
    if isinstance(data, dict):
        for key, fallback in _FALLBACK.items():
            value = data.get(key, fallback)
            if isinstance(fallback, bool) and isinstance(value, bool):
                merged[key] = value
            elif isinstance(fallback, int) and not isinstance(fallback, bool) and isinstance(value, int) and not isinstance(value, bool) and value > 0:
                merged[key] = value
            elif isinstance(fallback, str) and isinstance(value, str) and value.strip():
                merged[key] = value.strip()
    return merged


SETTINGS = load_settings()


def parse_version(text: object) -> tuple[int, int, int, int] | None:
    """(major, minor, patch, build) of a version string; None when it is not one."""
    if not isinstance(text, str) or VERSION_RE.fullmatch(text.strip()) is None:
        return None
    parts = [int(p) for p in text.strip().split(".")]
    return (parts[0], parts[1], parts[2], parts[3] if len(parts) == 4 else 0)


def compare(installed: object, latest: object) -> str:
    """"outdated" (a newer one exists), "current", "ahead" (this one is newer than the published one) or "unknown"."""
    a, b = parse_version(installed), parse_version(latest)
    if a is None or b is None:
        return "unknown"
    return "outdated" if a < b else "ahead" if a > b else "current"


def manifest_url(repository: str, settings: dict[str, Any] | None = None) -> str:
    cfg = settings or SETTINGS
    return f"{cfg['rawBase'].rstrip('/')}/{cfg['owner']}/{repository}/{cfg['branch']}/{cfg['manifestFile']}"


def manifest_version(body: object, expected_name: str | None = None) -> str | None:
    """The version of a manifest (text or already parsed), or None when it is not a manifest of this ecosystem."""
    try:
        data = json.loads(body) if isinstance(body, (str, bytes)) else body
    except ValueError:
        return None
    if not isinstance(data, dict) or data.get("ecosystem") != ECOSYSTEM_ID:
        return None
    if expected_name is not None and data.get("name") != expected_name:
        return None
    version = data.get("version")
    return version if isinstance(version, str) and parse_version(version) is not None else None


Fetcher = Callable[[str, float], str]


def fetch_text(url: str, timeout: float) -> str:
    """GET of a small text file. Only https addresses (or http to this machine, for tests) are opened."""
    if not (url.startswith("https://") or url.startswith("http://127.0.0.1") or url.startswith("http://localhost")):
        raise ValueError("only https addresses are read")
    request = urllib.request.Request(url, headers={"User-Agent": "hydra-umc-suite-update-check", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - the scheme was checked above
        return response.read(256 * 1024).decode("utf-8", "replace")


def api_state(remote_api_version: object, minimum: int | None = None) -> str:
    """"ok", "too_old" (the server speaks an older API than this program needs) or "unknown" (the server did not say)."""
    low = SETTINGS["minRemoteApiVersion"] if minimum is None else minimum
    if isinstance(remote_api_version, bool) or not isinstance(remote_api_version, int) or remote_api_version <= 0:
        return "unknown"
    return "ok" if remote_api_version >= low else "too_old"


def run_check(
    installed_suite: str,
    servers: Iterable[dict[str, Any]],
    fetch: Fetcher = fetch_text,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Reads the two manifests once and compares. `servers` are dicts with name, appVersion and remoteApiVersion. A manifest that
    cannot be read leaves its comparisons "unknown" and puts the reason in `errors`; nothing here raises."""
    cfg = settings or SETTINGS
    errors: list[str] = []

    def latest_of(repository: str) -> str | None:
        url = manifest_url(repository, cfg)
        try:
            version = manifest_version(fetch(url, float(cfg["timeoutSeconds"])), repository)
        except Exception as error:  # a network failure is an answer, not a crash
            errors.append(f"{repository}: {error}")
            return None
        if version is None:
            errors.append(f"{repository}: not a manifest of this ecosystem")
        return version

    latest_suite = latest_of(cfg["suiteRepository"])
    rows = list(servers)
    latest_server = latest_of(cfg["serverRepository"]) if rows else None
    return {
        "suite": {"installed": installed_suite, "latest": latest_suite, "state": compare(installed_suite, latest_suite)},
        "servers": [
            {
                "name": str(s.get("name") or "?"),
                "installed": str(s.get("appVersion") or ""),
                "latest": latest_server,
                "state": compare(s.get("appVersion"), latest_server),
                "apiVersion": s.get("remoteApiVersion") if isinstance(s.get("remoteApiVersion"), int) else 0,
                "api": api_state(s.get("remoteApiVersion"), int(cfg["minRemoteApiVersion"])),
            }
            for s in rows
        ],
        "errors": errors,
    }
