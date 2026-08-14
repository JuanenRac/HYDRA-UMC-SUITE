# =============================================================================
# HYDRA-UMC SUITE - net/discovery.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Subnet scanner - hits GET /api/hydra-info (docs/REMOTE_API.md section 1)
# on every candidate IP in a /24 range concurrently, keeps whichever ones
# actually answer with a real HYDRA-UMC STUDIO payload. No mDNS/Bonjour
# service exists on the server side yet (REMOTE_API.md's own "Future
# work" note) - a raw concurrent scan is the real, working option today,
# not a placeholder standing in for it.
# =============================================================================
from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import AsyncIterator

import httpx

from hydra_suite.models import ServerInfo

DEFAULT_PORT = 3000
SCAN_TIMEOUT_S = 0.6
SCAN_CONCURRENCY = 64


def local_ipv4_addresses() -> list[str]:
    """Every non-loopback IPv4 address this machine currently has - a
    machine on more than one network (Ethernet + Wi-Fi, or a VPN tunnel
    adapter) gets a candidate subnet per address, not just the first one
    found, since a HYDRA-UMC being scanned for might be reachable on any
    of them."""
    addrs: list[str] = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in addrs:
                addrs.append(ip)
    except OSError:
        pass
    if not addrs:
        # Fallback: open a dummy UDP "connection" (no packet actually
        # sent) to force the OS to pick a real outbound-routable local
        # address, same trick used when getaddrinfo's own hostname
        # lookup doesn't return anything useful (common on some
        # corporate-DNS-configured Windows machines).
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                addrs.append(s.getsockname()[0])
        except OSError:
            pass
    return addrs


def candidate_hosts_for(local_ip: str) -> list[str]:
    """Every other host in local_ip's own /24 - the overwhelmingly common
    case for a home/lab/office LAN. A HYDRA-UMC reachable only through a
    differently-sized subnet or a routed VPN tunnel won't be found by this
    scan - use the manual "Add server by address" path in the UI for
    those instead (see ui/panels/server_browser.py), which needs no
    special VPN-aware code at all: a VPN tunnel just makes a remote
    address reachable as if local, so a plain host:port connect already
    works through it once the tunnel itself is up."""
    try:
        network = ipaddress.ip_network(f"{local_ip}/24", strict=False)
    except ValueError:
        return []
    return [str(h) for h in network.hosts() if str(h) != local_ip]


async def probe_host(client: httpx.AsyncClient, host: str, port: int = DEFAULT_PORT) -> ServerInfo | None:
    """One GET /api/hydra-info - returns None for anything that doesn't
    answer or doesn't answer with a recognizable HYDRA-UMC STUDIO payload
    (a closed port, a different service entirely, or a malformed response
    all look the same from here: "not a real server", not an error worth
    surfacing per-host during a broad scan)."""
    try:
        resp = await client.get(f"http://{host}:{port}/api/hydra-info", timeout=SCAN_TIMEOUT_S)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not isinstance(data, dict) or data.get("product") != "HYDRA-UMC STUDIO":
            return None
        return ServerInfo.from_hydra_info(host, port, data)
    except (httpx.HTTPError, ValueError):
        return None


async def scan_subnets(hosts: list[str] | None = None, port: int = DEFAULT_PORT) -> AsyncIterator[ServerInfo]:
    """Scans every candidate host across every local subnet concurrently
    (bounded by SCAN_CONCURRENCY, so a /24-times-N-interfaces scan doesn't
    open hundreds of sockets at once), yielding each real HYDRA-UMC found
    as soon as it answers rather than waiting for the whole scan to
    finish - the server browser panel can start listing results
    immediately instead of showing a blank list for the full scan
    duration.
    """
    if hosts is None:
        hosts = []
        for local_ip in local_ipv4_addresses():
            hosts.extend(candidate_hosts_for(local_ip))
    if not hosts:
        return

    semaphore = asyncio.Semaphore(SCAN_CONCURRENCY)
    queue: asyncio.Queue[ServerInfo | None] = asyncio.Queue()
    remaining = len(hosts)

    async def worker(host: str) -> None:
        nonlocal remaining
        async with semaphore:
            async with httpx.AsyncClient() as client:
                result = await probe_host(client, host, port)
        await queue.put(result)

    tasks = [asyncio.create_task(worker(h)) for h in hosts]

    try:
        for _ in range(len(hosts)):
            result = await queue.get()
            if result is not None:
                yield result
    finally:
        for t in tasks:
            t.cancel()
