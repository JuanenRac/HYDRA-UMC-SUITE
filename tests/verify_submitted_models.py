# =============================================================================
# HYDRA-UMC SUITE - tests/verify_submitted_models.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies how the models that the editors submitted to the server are read, without any window: the list (newest
# first, what is not a model skipped), the download path (every part encoded), the name a URDF is saved under (one
# plain name, never a path the server chose) and the sentences about a failure.
# =============================================================================
import sys

sys.path.insert(0, ".")

from hydra_suite.i18n import _
from hydra_suite.panel_logic import submitted_models as sm

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


models = sm.parse_models({
    "models": [
        {"slug": "b", "name": "Beta", "category": "robots", "submittedAt": "2030-01-01T10:00:00.000Z"},
        {"slug": "a", "name": "Alpha", "category": "robots", "submittedAt": "2030-01-02T10:00:00.000Z"},
        {"slug": "c", "category": "tools"},
        {"slug": "d", "name": "Delta", "category": "tools"},
        {"name": "No slug", "category": "robots"},
        {"slug": "x"},
        "junk", None, 42,
    ],
})
check("the models, newest first and then by name", [m["slug"] for m in models], ["a", "b", "c", "d"])
check("a model without a name shows its slug and one without a date has none", (models[2]["name"], models[2]["submittedAt"]), ("c", ""))
for bad in (None, 3, "x", [], {}, {"models": "many"}, {"models": {}}):
    check(f"not a list of models: {bad!r}", sm.parse_models(bad), [])
shown = sm.rows(models)
check("the rows show the date without the milliseconds, or a dash", (shown[0]["submitted"], shown[2]["submitted"]), ("2030-01-02 10:00:00", "-"))
check("the download path encodes every part", (sm.download_path("robots", "ar3"), sm.download_path("a/b", "../x?y")), ("/api/models/robots/ar3/download", "/api/models/a%2Fb/..%2Fx%3Fy/download"))
check("a URDF is saved under one plain name", [sm.urdf_file_name(a, "ar3") for a in ({"urdfFilename": "ar3.urdf"}, {"urdfFilename": "../../etc/evil.urdf"}, {"urdfFilename": r"C:\Windows\evil.urdf"}, {"urdfFilename": "evil.exe"}, {"urdfFilename": ""}, None, {"urdfFilename": 7})],
      ["ar3.urdf", "evil.urdf", "evil.urdf", "ar3.urdf", "ar3.urdf", "ar3.urdf", "ar3.urdf"])
check("a slug that is not a plain name becomes model.urdf", sm.urdf_file_name(None, "../x"), "model.urdf")
check("the URDF text only when the answer has some", (sm.urdf_text({"urdfXml": "<robot/>"}), sm.urdf_text({"urdfXml": "  "}), sm.urdf_text({"urdfXml": 3}), sm.urdf_text(None)), ("<robot/>", None, None, None))
check("the sentences about a failure", (sm.failure_text(0), sm.failure_text(401), sm.failure_text(403), sm.failure_text(500)), (_("MODELS_ERROR_NETWORK"), _("MODELS_ERROR_LOGIN"), _("MODELS_ERROR_LOGIN"), _("MODELS_ERROR_SERVER")))

print("FAILURES:", failures)
sys.exit(1 if failures else 0)
