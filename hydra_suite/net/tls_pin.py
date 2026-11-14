# =============================================================================
# HYDRA-UMC SUITE - hydra_suite/net/tls_pin.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Pins the certificate of a HYDRA-UMC-SERVER, per server, with a switch that is OFF by default.

Off (the default) a server over HTTPS is checked against the public certificate authorities only, as before: a server with a
self-signed certificate is then refused. With the switch on, the person can pin the certificate a server shows: the
program reads it (nothing is sent to the server but the handshake), shows its SHA-256 fingerprint so it can be compared with
the one on the server, and keeps the certificate under the address of that server. From then on a connection to that
address trusts exactly that certificate and nothing else (a different certificate for the same address is refused, whoever
signed it); an address with no pin keeps using the public authorities.

The configuration (`hydra_suite_config.json`) holds:

    "tlsPinning": {"enabled": false, "servers": {"192.168.0.180:3000": {"fingerprint": "AB:CD:...", "pem": "-----BEGIN CERTIFICATE-----..."}}}

Nothing here ever sends a credential: the certificate is read with a bare handshake.
"""
from __future__ import annotations

import hashlib
import socket
import ssl
from typing import Any

CONFIG_KEY = "tlsPinning"


class PinError(ValueError):
    """A certificate that cannot be read or pinned."""


def server_key(host: str, port: int) -> str:
    """The address a pin belongs to, in one spelling (host in lower case, with the port)."""
    return f"{host.strip().lower()}:{int(port)}"


def fingerprint_of_der(der: bytes) -> str:
    """SHA-256 of the DER certificate as upper-case hexadecimal pairs separated by colons."""
    digest = hashlib.sha256(der).hexdigest().upper()
    return ":".join(digest[i : i + 2] for i in range(0, len(digest), 2))


def fingerprint_of_pem(pem: str) -> str:
    try:
        return fingerprint_of_der(ssl.PEM_cert_to_DER_cert(pem))
    except (ValueError, ssl.SSLError) as error:
        raise PinError(f"not a certificate: {error}") from error


def read_settings(config: dict[str, Any]) -> tuple[bool, dict[str, dict[str, str]]]:
    """(enabled, pins) from the configuration; anything that is not shaped as above counts as off and empty."""
    section = config.get(CONFIG_KEY)
    if not isinstance(section, dict):
        return False, {}
    enabled = section.get("enabled") is True
    pins: dict[str, dict[str, str]] = {}
    servers = section.get("servers")
    if isinstance(servers, dict):
        for key, entry in servers.items():
            if isinstance(key, str) and isinstance(entry, dict) and isinstance(entry.get("pem"), str) and isinstance(entry.get("fingerprint"), str):
                pins[key] = {"fingerprint": entry["fingerprint"], "pem": entry["pem"]}
    return enabled, pins


def fetch_certificate(host: str, port: int, timeout: float = 5.0) -> tuple[str, str]:
    """(PEM, fingerprint) of the certificate the server shows. Only the handshake is made; nothing is trusted or sent."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((host, int(port)), timeout=timeout) as raw, context.wrap_socket(raw, server_hostname=host) as tls:
            der = tls.getpeercert(binary_form=True)
    except (OSError, ssl.SSLError) as error:
        raise PinError(f"cannot read the certificate of {host}:{port}: {error}") from error
    if not der:
        raise PinError(f"{host}:{port} showed no certificate")
    return ssl.DER_cert_to_PEM_cert(der), fingerprint_of_der(der)


def pin_entry(config: dict[str, Any], host: str, port: int, pem: str, expected_fingerprint: str = "") -> dict[str, Any]:
    """The `tlsPinning` section with the certificate pinned for host:port. With `expected_fingerprint` the pin is refused unless the
    certificate has exactly that fingerprint (what the person read on the server)."""
    fingerprint = fingerprint_of_pem(pem)
    if expected_fingerprint and _normalize(expected_fingerprint) != _normalize(fingerprint):
        raise PinError("the fingerprint of the certificate is not the one expected")
    enabled, pins = read_settings(config)
    pins[server_key(host, port)] = {"fingerprint": fingerprint, "pem": pem}
    return {"enabled": enabled, "servers": pins}


def unpin_entry(config: dict[str, Any], host: str, port: int) -> dict[str, Any]:
    enabled, pins = read_settings(config)
    pins.pop(server_key(host, port), None)
    return {"enabled": enabled, "servers": pins}


def with_enabled(config: dict[str, Any], enabled: bool) -> dict[str, Any]:
    _, pins = read_settings(config)
    return {"enabled": bool(enabled), "servers": pins}


def _normalize(fingerprint: str) -> str:
    return "".join(ch for ch in fingerprint.upper() if ch in "0123456789ABCDEF")


def verify_for(config: dict[str, Any], host: str, port: int) -> ssl.SSLContext | bool:
    """What to pass as `verify` (httpx) or `ssl` (websockets) for this server: True (the default checks) while the switch is off or the
    address has no pin; with a pin, a context that trusts exactly the pinned certificate and checks no host name (the certificate
    itself is the identity)."""
    enabled, pins = read_settings(config)
    pin = pins.get(server_key(host, port)) if enabled else None
    if pin is None:
        return True
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = False
    # the pinned certificate is its own anchor: allow a leaf as the end of the chain, and do not insist on the extensions a CA would carry
    context.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    try:
        context.load_verify_locations(cadata=pin["pem"])
    except (ssl.SSLError, ValueError) as error:
        raise PinError(f"the pinned certificate of {server_key(host, port)} cannot be loaded: {error}") from error
    return context
