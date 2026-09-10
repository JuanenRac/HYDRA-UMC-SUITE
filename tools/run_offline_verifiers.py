#!/usr/bin/env python3
# =============================================================================
# HYDRA-UMC-SUITE - tools/run_offline_verifiers.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# REV-019 (P2): neither this
# repository's own tools/build_test.py nor .github/workflows/ci.yml ever
# ran the real Qt/backend control verifiers under tests/verify_*.py -
# both only ever compiled Python sources. A real, deterministic
# regression in any one of them (a disconnected button, a control that
# stopped reflecting real state, a panel that crashes on construction)
# could reach main with a fully green CI, and the only way anyone would
# notice is by remembering to run that one script by hand.
#
# This runner discovers every tests/verify_*.py script and runs each as
# its own subprocess under a headless Qt platform
# (QT_QPA_PLATFORM=offscreen), so it needs no real display and behaves
# the same on a developer's desktop and on CI. It deliberately never
# discovers tests/test_net_manual.py - that script needs a real,
# already-running HYDRA-UMC-SERVER on localhost:3000 (see its own
# header) and is exactly the kind of "manual test with a real server"
# the review's own finding says must stay clearly excluded from this
# automatic, offline gate.
#
# None of the tests/verify_*.py scripts open a real network connection
# or send a command to a real server/robot - each one's own header
# states the exact fake/mocked boundary it verifies against (the same
# "verify the real logic without the real hardware/network" convention
# this ecosystem applies everywhere else).
# =============================================================================
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = ROOT / "tests"


def discover_verifiers() -> list[Path]:
    """Every tests/verify_*.py script, in a stable, repeatable order.

    Named `verify_*` (not `test_*`) on purpose, matching this repo's own
    existing convention - `test_net_manual.py` (needs a real server) is
    excluded by the glob itself, not by an exception list that could go
    stale.
    """
    return sorted(TESTS_DIR.glob("verify_*.py"))


def main() -> int:
    scripts = discover_verifiers()
    if not scripts:
        print("OFFLINE_VERIFIERS=FAIL no tests/verify_*.py scripts were found", file=sys.stderr)
        return 1

    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"

    failures: list[str] = []
    for script in scripts:
        label = str(script.relative_to(ROOT))
        print(f"--- {label} " + "-" * max(1, 70 - len(label)))
        result = subprocess.run([sys.executable, str(script)], cwd=ROOT, env=env)
        if result.returncode != 0:
            failures.append(label)

    print()
    if failures:
        print(f"OFFLINE_VERIFIERS=FAIL {len(failures)}/{len(scripts)} script(s) failed:")
        for name in failures:
            print(f"  - {name}")
        return 1

    print(f"OFFLINE_VERIFIERS=PASS {len(scripts)} script(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
