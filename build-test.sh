#!/usr/bin/env bash
# HYDRA_UMC_SCRIPT_STANDARD_HEADER_BEGIN
# *****************************************************************************
# Project   : HYDRA-UMC-SUITE
# Script    : build-test.sh
# Purpose   : Non-mutating build validation; manifest and CHANGELOG stay unchanged.
# Author    : JuanenRac (Electro Hobby 3D)
# Email     : electrohobby3d@gmail.com
# Copyright : (C) 2026 JuanenRac
# License   : GPL-3.0 - see LICENSE
# *****************************************************************************
# HYDRA_UMC_SCRIPT_STANDARD_HEADER_END
# HYDRA_UMC_SCRIPT_STANDARD_BANNER_BEGIN
printf '\n*******************************************************************************\n'
printf '%s\n' "* HYDRA-UMC-SUITE - build-test.sh"
printf '%s\n' "* Mode      : NON-MUTATING BUILD TEST"
printf '%s\n' "* Author    : JuanenRac (Electro Hobby 3D)"
printf '%s\n' "* Email     : electrohobby3d@gmail.com"
printf '%s\n' "* Copyright : (C) 2026 JuanenRac"
printf '%s\n' "* License   : GPL-3.0 - see LICENSE"
printf '%s\n' "* ------------------------------------------------------------------------- *"
printf '%s\n' "* 1. Run the project's build validation command."
printf '%s\n' "* 2. Do not change the project version, manifest or CHANGELOG."
printf '%s\n' "* 3. Report the result and keep an interactive terminal open."
printf '%s\n' "*******************************************************************************"
printf '\n'
# HYDRA_UMC_SCRIPT_STANDARD_BANNER_END
# Runs the non-versioning build check. It does not update the manifest or CHANGELOG.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Real bug fixed here: unlike run.sh/build_exe.sh, this never activated
# .venv before invoking python3 - on a machine where numpy/PySide6/httpx/
# qasync are only installed in .venv (the normal, correct setup after
# build_exe.sh/bat), every one of the 27 offline verifiers failed with
# ModuleNotFoundError, looking exactly like the whole build was broken
# when the real project was fine - a live report confirmed this exact
# reproduction.
if [ -f "$ROOT/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$ROOT/.venv/bin/activate"
elif [ -f "$ROOT/.venv/Scripts/activate" ]; then
    # shellcheck disable=SC1091
    source "$ROOT/.venv/Scripts/activate"
fi
python3 "$ROOT/tools/build_test.py"
status=$?
echo
if [ -t 0 ]; then
    read -r -p "Press Enter to close this window..." _
fi
exit "$status"