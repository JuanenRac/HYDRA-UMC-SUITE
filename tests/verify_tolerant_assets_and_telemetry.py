# =============================================================================
# HYDRA-UMC SUITE - tests/verify_tolerant_assets_and_telemetry.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Verifies that damaged data does not take the program down:
#   - the heated bed and vacuum table catalogs fall back to one built-in
#     model when catalog.json is missing, not JSON, or has no usable model
#   - the telemetry chart helper leaves out null / text / NaN values and
#     entries without a time instead of raising
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")

from hydra_suite import heated_beds, vacuum_tables
from hydra_suite.panel_logic.ecosystem_telemetry import clean_points

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def catalog_dir(text):
    folder = Path(tempfile.mkdtemp())
    if text is not None:
        (folder / "catalog.json").write_text(text, encoding="utf-8")
    return folder


for label, text in (
    ("missing file", None),
    ("not JSON", "{broken"),
    ("no models key", "{}"),
    ("models is not a list", '{"models": 5}'),
    ("no usable model", '{"models": [1, {"id": "x"}]}'),
):
    folder = catalog_dir(text)
    beds = heated_beds._load_catalog(folder)
    check(f"heated beds, {label}: one fallback model", len(beds["models"]), 1)
    check(f"heated beds, {label}: default exists", beds["defaultModelId"], beds["models"][0]["id"])
    check(f"vacuum tables, {label}: one fallback model", len(vacuum_tables._load_models(folder)), 1)

good = catalog_dir(json.dumps({"defaultModelId": "gone", "models": [{"id": "a", "width": 10, "length": 20}, "junk"]}))
loaded = heated_beds._load_catalog(good)
check("heated beds: junk entries dropped", [m["id"] for m in loaded["models"]], ["a"])
check("heated beds: unknown default replaced", loaded["defaultModelId"], "a")
check("the real catalogs still load", len(heated_beds.HEATED_BED_MODELS) > 1 and len(vacuum_tables.VACUUM_TABLE_MODELS) > 1, True)

points = [
    {"timestamp": 1000, "value": 1.5},
    {"timestamp": 2000, "value": None},
    {"timestamp": 3000, "value": "7"},
    {"timestamp": 4000, "value": float("nan")},
    {"value": 3},
    {"timestamp": 5000, "value": True},
    "junk",
    {"timestamp": 6000, "value": 2},
]
check("telemetry: only complete numeric points stay", clean_points(points, "timestamp"), [(1000.0, 1.5), (6000.0, 2.0)])
check("telemetry: not a list gives nothing", clean_points({"a": 1}, "timestamp"), [])

print("FAILURES:", failures)
sys.exit(1 if failures else 0)
