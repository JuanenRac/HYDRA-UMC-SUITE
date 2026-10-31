# =============================================================================
# HYDRA-UMC-SUITE - tests/test_offline_verifiers.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""pytest as the runner of the verifiers: one test per verifier script, run the way `tools/run_offline_verifiers.py` runs it.

The verifiers (`tests/verify_*.py` and `verify_qt_suite_shell.py`) stay what they are, scripts that exit non-zero
on a failed check; this file only gives the CI a per-verifier report (names, durations, JUnit XML with `--junitxml`).
Each one runs in its own process under the headless Qt platform, so no display is needed and none of them can leave
state behind for the next.

    python -m pytest tests/test_offline_verifiers.py -q
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from run_offline_verifiers import discover_verifiers, ensure_meshes  # noqa: E402

VERIFIERS = discover_verifiers()


@pytest.fixture(scope="session", autouse=True)
def meshes_present() -> None:
    """The verifiers read the 3D models; they come from the pinned package when the tree does not carry them."""
    assert ensure_meshes() == 0, "the 3D models are missing and could not be fetched (see the message above)"


@pytest.mark.parametrize("script", VERIFIERS, ids=lambda path: str(path.relative_to(ROOT)).replace(os.sep, "/"))
def test_verifier_passes(script: Path) -> None:
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    result = subprocess.run(
        [sys.executable, str(script)], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
    )
    assert result.returncode == 0, (result.stdout + result.stderr)[-4000:]


def test_the_verifiers_were_found() -> None:
    assert VERIFIERS
