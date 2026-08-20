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
from hydra_suite.net.client import HYDRA_CLIENT_HEADERS

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
    # Always also try the UDP "connection" trick (no packet actually sent,
    # just forces the OS routing table to pick a real outbound-facing
    # address) and merge its result in - not only as a last-resort fallback
    # when getaddrinfo returned nothing. Windows's hostname-based lookup
    # above only returns the address(es) already registered against the
    # local computer name, and on a machine with more than one adapter
    # (a Wi-Fi card plus a VPN client, Docker Desktop's internal NAT
    # adapter, Hyper-V/VMware virtual switches, etc.) that registration can
    # easily point at an inactive/virtual adapter instead of - or as well
    # as - the one actually holding the default route to the LAN a
    # HYDRA-UMC server lives on. getaddrinfo() returning SOMETHING is not
    # the same as it returning the RIGHT thing, so the routing-table trick
    # needs to run and be merged in every time, not just when the hostname
    # lookup came back completely empty.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            routed_ip = s.getsockname()[0]
        if routed_ip not in addrs:
            addrs.append(routed_ip)
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


# Every field a real HYDRA-UMC STUDIO server's GET /api/hydra-info always
# includes together (see server.ts's own /api/hydra-info route) - this is
# what actually identifies the payload as coming from a real server. The
# "product" field is deliberately NOT part of that check: server-side it's
# `realSettings(lastKnownSettings)?.serverName || "HYDRA-UMC STUDIO"` - the
# server's own user-editable display name (Config > Identity in the browser
# UI), which reads "HYDRA-UMC STUDIO" only for a server that has never been
# renamed. Matching it against that literal string would recognize a
# factory-named server and silently fail to recognize any server the owner
# has renamed (a normal, UI-invited customization) even though it answers
# with a perfectly valid payload - identifying by the payload's stable
# structural shape instead means a renamed server is found exactly like an
# un-renamed one. Manual "Add server by address" was never affected by this
# distinction, since it talks to /api/settings instead, which carries no
# "product"-like field at all.
_HYDRA_INFO_REQUIRED_KEYS = ("remoteApiVersion", "appVersion", "hostname", "controllerCount", "robotCount")


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
        if not isinstance(data, dict) or not all(key in data for key in _HYDRA_INFO_REQUIRED_KEYS):
            return None
        if not isinstance(data.get("remoteApiVersion"), int):
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
        # "127.0.0.1" first, always - the single most common real setup
        # (documented in the project spec) is HYDRA-UMC STUDIO's own dev
        # server running on the SAME machine as SUITE, which
        # candidate_hosts_for() below deliberately excludes (it only
        # returns OTHER hosts on the subnet) and local_ipv4_addresses()
        # never returns in the first place (loopback is filtered there on
        # purpose, since scanning the whole 127.0.0.0/24 range would be
        # pointless) - without this, a same-machine server was never
        # actually probed by the "auto-detect" scan at all.
        hosts = ["127.0.0.1"]
        local_ips = local_ipv4_addresses()
        for local_ip in local_ips:
            if local_ip not in hosts:
                hosts.append(local_ip)  # the machine's own LAN IP - a server bound to it (not just localhost) answers here too
            hosts.extend(candidate_hosts_for(local_ip))
    if not hosts:
        return

    semaphore = asyncio.Semaphore(SCAN_CONCURRENCY)
    queue: asyncio.Queue[ServerInfo | None] = asyncio.Queue()
    remaining = len(hosts)

    async def worker(host: str) -> None:
        nonlocal remaining
        async with semaphore:
            async with httpx.AsyncClient(headers=HYDRA_CLIENT_HEADERS) as client:
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
