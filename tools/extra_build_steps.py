#!/usr/bin/env python3
# =============================================================================
# HYDRA-UMC-SUITE - tools/extra_build_steps.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The steps of this repository beyond the shared build test: the offline Qt/backend verifiers."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def fail(message: str) -> None:
    print(f"BUILD_TEST=FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def run(*command: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command))
    try:
        subprocess.run(command, cwd=cwd, env=env, check=True)
    except FileNotFoundError:
        fail(f"required command not found: {command[0]}")
    except subprocess.CalledProcessError as exc:
        fail(f"command failed with exit code {exc.returncode}: {' '.join(command)}")


def main() -> int:
    # The Qt/backend control verifiers (tests/verify_*.py), run headless by their own runner.
    offline_verifiers = ROOT / "tools" / "run_offline_verifiers.py"
    if offline_verifiers.is_file():
        run(sys.executable, str(offline_verifiers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
