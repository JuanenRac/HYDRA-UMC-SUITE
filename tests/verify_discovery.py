# =============================================================================
# HYDRA-UMC SUITE - tests/verify_discovery.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# net/discovery.py's subnet-scan and real mDNS discovery paths are both
# real and already ship (see that module's own header comment) - what
# had zero automated coverage until now is the pure, deterministic logic
# around them: candidate_hosts_for()'s /24 enumeration, and
# discover_servers()'s own (host, port) dedup across its two concurrent
# sources. test_net_manual.py already covers probe_host() end-to-end, but
# only against a real, already-running HYDRA-UMC STUDIO server - it
# can't run in CI and never exercises this logic at all. This script
# needs no network, no real server, and no zeroconf multicast socket -
# just candidate_hosts_for() (pure) and discover_servers() with its two
# real sources monkeypatched to fake async generators, same "verify the
# real logic without the real hardware/network" boundary this ecosystem
# applies everywhere else.
# =============================================================================
import asyncio
import sys
sys.path.insert(0, ".")

from hydra_suite.models import ServerInfo
from hydra_suite.net import discovery

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


# --- candidate_hosts_for(): pure /24 enumeration --------------------------

hosts = discovery.candidate_hosts_for("192.168.1.50")
check("candidate_hosts_for count (254 - self)", len(hosts), 253)
check("candidate_hosts_for excludes local_ip", "192.168.1.50" in hosts, False)
check("candidate_hosts_for includes .1", "192.168.1.1" in hosts, True)
check("candidate_hosts_for includes .254", "192.168.1.254" in hosts, True)
check("candidate_hosts_for excludes .0/.255 (network/broadcast)", "192.168.1.0" in hosts, False)

check("candidate_hosts_for malformed input degrades to empty, not a raise", discovery.candidate_hosts_for("not-an-ip"), [])


# --- discover_servers(): (host, port) dedup across both real sources -----
# Neither source's own real implementation runs here - both are
# monkeypatched to fake async generators, so this exercises exactly the
# merge/dedup logic discover_servers() itself owns, deterministically.

SAME = ServerInfo(host="10.0.0.5", port=3000, hostname="same-both-sources")
ONLY_SCAN = ServerInfo(host="10.0.0.6", port=3000, hostname="only-scan")
ONLY_MDNS = ServerInfo(host="10.0.0.7", port=3000, hostname="only-mdns")


async def fake_scan_subnets(hosts=None, port=3000):
    yield SAME
    yield ONLY_SCAN


async def fake_discover_mdns(timeout=4.0):
    yield SAME  # same (host, port) the fake scan already yielded
    yield ONLY_MDNS


async def run_merge_check():
    original_scan, original_mdns = discovery.scan_subnets, discovery.discover_mdns
    discovery.scan_subnets = fake_scan_subnets
    discovery.discover_mdns = fake_discover_mdns
    try:
        results = [info async for info in discovery.discover_servers()]
    finally:
        discovery.scan_subnets = original_scan
        discovery.discover_mdns = original_mdns
    return results


results = asyncio.run(run_merge_check())
hostnames = sorted(r.hostname for r in results)
check("discover_servers yields 3 distinct (host, port) entries, not 4", len(results), 3)
check("discover_servers dedups the entry both fakes yielded", hostnames, ["only-mdns", "only-scan", "same-both-sources"])

print()
if failures:
    print(f"FAILED: {failures} mismatches")
    sys.exit(1)
else:
    print("ALL DISCOVERY CHECKS PASSED (candidate_hosts_for + discover_servers dedup)")
