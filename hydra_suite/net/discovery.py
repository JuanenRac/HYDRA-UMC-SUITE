# =============================================================================
# HYDRA-UMC SUITE - net/discovery.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Two independent discovery paths, merged by discover_servers() at the
# bottom of this file into the one stream ui/panels/server_browser.py's
# scan button actually consumes:
#   - scan_subnets(): brute-force GET /api/hydra-info (docs/REMOTE_API.md
#     section 1) against every candidate IP in a /24 range concurrently -
#     slower, but needs no multicast delivery at all, so it stays the
#     guaranteed fallback (a locked-down network, a VLAN that blocks
#     multicast, a Windows Firewall profile that drops inbound UDP 5353,
#     etc. all still work here).
#   - discover_mdns(): real mDNS/Bonjour, querying the "_hydra._tcp"
#     service HYDRA-UMC STUDIO's own server.ts actually publishes (see
#     that project's setupDiscovery(): `bonjour.publish({ name:
#     serverName, type: 'hydra', port: 3000 })`, via the `bonjour-service`
#     npm package) - near-instant on a network that delivers the
#     multicast replies. This is NOT a placeholder standing in for a
#     server-side feature that doesn't exist yet - server.ts has
#     published this since before this file was first written; this
#     client simply never queried for it. Same service name
#     HYDRA-UMC-IOS-CONTROL's own net/discovery.dart already queries
#     (`_hydra._tcp.local`, see that file's header comment) - SUITE is
#     not inventing a new convention here, just adopting the existing
#     one.
# =============================================================================
from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import AsyncIterator

import httpx
from zeroconf import IPVersion, ServiceStateChange
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf

from hydra_suite.models import ServerInfo
from hydra_suite.net.client import HYDRA_CLIENT_HEADERS

DEFAULT_PORT = 3000
SCAN_TIMEOUT_S = 0.6
SCAN_CONCURRENCY = 64

# server.ts's `bonjour.publish({ type: 'hydra', ... })` becomes
# "_hydra._tcp.local." on the wire per standard DNS-SD naming (the
# library adds the underscores/".local."/protocol suffix around the bare
# `type` string) - this has to match that exactly or the browser below
# silently discovers nothing.
MDNS_SERVICE_TYPE = "_hydra._tcp.local."
MDNS_TIMEOUT_S = 4.0
MDNS_RESOLVE_TIMEOUT_MS = 3000


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

    # Two local IPv4 addresses can land in the same /24 (a VPN/virtual
    # adapter sharing the real LAN's range is a normal case, not exotic -
    # local_ipv4_addresses() above deliberately returns every adapter's
    # address, not just one), which made candidate_hosts_for() get called
    # once per local IP and append practically the same host range twice -
    # every host in the overlap got scanned in parallel by two separate
    # worker tasks for no benefit (add_server() in app.py already dedupes
    # by host:port so no duplicate rows ever reached the UI, but the
    # wasted connections were real). dict.fromkeys() dedupes while
    # preserving scan order (127.0.0.1 first, as intended above).
    hosts = list(dict.fromkeys(hosts))

    semaphore = asyncio.Semaphore(SCAN_CONCURRENCY)
    queue: asyncio.Queue[ServerInfo | None] = asyncio.Queue()

    async def worker(host: str) -> None:
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


async def discover_mdns(timeout: float = MDNS_TIMEOUT_S) -> AsyncIterator[ServerInfo]:
    """Real mDNS/Bonjour discovery against the "_hydra._tcp" service
    server.ts actually publishes - see this file's header comment for the
    exact server.ts call this queries for and why MDNS_SERVICE_TYPE has
    to match it exactly.

    Every service instance the browser reports is still verified with a
    real GET /api/hydra-info probe (probe_host, the same one scan_subnets
    uses) before being yielded - a name showing up on mDNS is only ever
    treated as "worth probing", never assumed to be a live, real HYDRA-UMC
    STUDIO server just because Bonjour answered (mDNS records can be
    stale, or - once other quiet devices exist on the LAN - could
    coincidentally reuse "_hydra._tcp.local." for something unrelated).
    This mirrors exactly how HYDRA-UMC-IOS-CONTROL's own discoverMdns()
    resolves-then-verifies with its own GET /api/hydra-info call rather
    than trusting the mDNS records alone.

    Best-effort like the Dart implementation too: no local multicast
    socket (locked-down network profile, firewall dropping inbound UDP
    5353, a VPN-only adapter with no real multicast path), zeroconf
    raising during setup, or a timeout with zero replies all just end the
    generator early with whatever (possibly nothing) was already found -
    discover_servers() below keeps scan_subnets() running independently
    either way, so a network where mDNS doesn't work still gets found via
    the brute-force scan.
    """
    seen: set[tuple[str, int]] = set()
    found_names: asyncio.Queue[str] = asyncio.Queue()

    def on_service_state_change(zeroconf, service_type, name, state_change, **_kwargs) -> None:
        if state_change in (ServiceStateChange.Added, ServiceStateChange.Updated):
            found_names.put_nowait(name)

    try:
        aiozc = AsyncZeroconf()
    except Exception:
        # No usable multicast socket on this machine/network - see
        # docstring above, this is an expected outcome, not a bug.
        return

    try:
        browser = AsyncServiceBrowser(aiozc.zeroconf, MDNS_SERVICE_TYPE, handlers=[on_service_state_change])
        try:
            async with httpx.AsyncClient(headers=HYDRA_CLIENT_HEADERS) as client:
                loop = asyncio.get_running_loop()
                deadline = loop.time() + timeout
                while True:
                    remaining = deadline - loop.time()
                    if remaining <= 0:
                        break
                    try:
                        name = await asyncio.wait_for(found_names.get(), timeout=remaining)
                    except (asyncio.TimeoutError, TimeoutError):
                        break
                    info = AsyncServiceInfo(MDNS_SERVICE_TYPE, name)
                    try:
                        resolved = await info.async_request(aiozc.zeroconf, MDNS_RESOLVE_TIMEOUT_MS)
                    except Exception:
                        continue
                    if not resolved or info.port is None:
                        continue
                    for host in info.parsed_addresses(IPVersion.V4Only):
                        key = (host, info.port)
                        if key in seen:
                            continue
                        seen.add(key)
                        result = await probe_host(client, host, info.port)
                        if result is not None:
                            yield result
        finally:
            await browser.async_cancel()
    finally:
        await aiozc.async_close()


async def discover_servers(
    hosts: list[str] | None = None, port: int = DEFAULT_PORT, mdns_timeout: float = MDNS_TIMEOUT_S
) -> AsyncIterator[ServerInfo]:
    """What ui/panels/server_browser.py's scan button actually calls:
    scan_subnets() (the guaranteed brute-force fallback) and
    discover_mdns() (near-instant when multicast delivery works) running
    CONCURRENTLY - not one after the other, and mDNS is additive here,
    not a replacement for the scan - see this file's header comment and
    HYDRA-UMC-IOS-CONTROL's own login_screen.dart, which runs its two
    equivalent paths the same way for the same reason.

    Deduplicates by (host, port) across BOTH sources - the same server
    quite plausibly answers to both at once (the most common real case:
    a same-machine dev server found via 127.0.0.1 through the subnet
    scan AND via its own LAN mDNS announcement). scan_subnets()'s own
    internal host-list dedup and discover_mdns()'s own per-instance
    `seen` set only prevent re-probing the SAME host from within ONE
    source; this is the one place that also prevents the SAME server
    from being yielded twice when both sources separately find it.
    add_server() in app.py additionally dedupes by "host:port" connection
    id, so even without this a duplicate would never have reached the
    UI as a second row - but yielding it twice here would still mean
    probing/verifying it twice for nothing, and would double-count
    _run_scan()'s own "N found" progress label in server_browser.py.
    """
    seen: set[tuple[str, int]] = set()
    queue: asyncio.Queue[ServerInfo | None] = asyncio.Queue()

    async def pump(gen: AsyncIterator[ServerInfo]) -> None:
        async for info in gen:
            await queue.put(info)
        await queue.put(None)

    tasks = [
        asyncio.create_task(pump(scan_subnets(hosts, port))),
        asyncio.create_task(pump(discover_mdns(mdns_timeout))),
    ]
    pending = len(tasks)
    try:
        while pending:
            item = await queue.get()
            if item is None:
                pending -= 1
                continue
            key = (item.host, item.port)
            if key in seen:
                continue
            seen.add(key)
            yield item
    finally:
        for t in tasks:
            t.cancel()
