# =============================================================================
# HYDRA-UMC SUITE - tests/verify_service_badges_and_log_handler.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies, with no server and no window, the colour and the word shown for a service on every combination of what systemd
# says and what the health check says (a failed unit or a dead check is never shown green), that each word exists in the
# eight languages, and the handler that feeds the Logs panel (one signal per record, a broken formatter does not stop the
# log, installing it twice attaches it once).
# =============================================================================
import logging
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, ".")

from hydra_suite import i18n, logging_handler
from hydra_suite.panel_logic import ecosystem_services as svc

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


ACTIVE_STATES = [None, "active", "failed", "inactive", "activating", "deactivating"]
LIVE_VALUES = [None, True, False]

# --- the colour: every combination, and the rule that nothing broken is green --------------------------------------
for state in ACTIVE_STATES:
    for live in LIVE_VALUES:
        project = {"activeState": state, "live": live}
        colour = svc._health(project)
        check(f"state={state} live={live}: a known colour", colour in svc._HEALTH_COLOR, True)
        broken = state == "failed" or live is False or state in ("inactive", "activating", "deactivating")
        check(f"state={state} live={live}: broken is never green", not (broken and colour == "green"), True)
check("nothing known is slate", svc._health({}), "slate")
check("active and answering is green", svc._health({"activeState": "active", "live": True}), "green")
check("active and answering nothing about health is green", svc._health({"activeState": "active"}), "green")
check("a failed unit is amber whatever the check says", [svc._health({"activeState": "failed", "live": v}) for v in LIVE_VALUES], ["amber"] * 3)
check("active but dead is amber", svc._health({"activeState": "active", "live": False}), "amber")
check("a stopped unit is red", svc._health({"activeState": "inactive"}), "red")
check("not a service: the check decides", (svc._health({"live": True}), svc._health({"live": False})), ("green", "red"))

# --- the word -----------------------------------------------------------------------------------------------------------
KEYS = {
    (None, None): "LBL_SERVICES_NOT_A_SERVICE",
    (None, True): "LBL_SERVICES_LIVE",
    (None, False): "LBL_SERVICES_DEAD",
    ("active", None): "LBL_SERVICES_RUNNING",
    ("active", True): "LBL_SERVICES_LIVE",
    ("active", False): "LBL_SERVICES_ERROR",
    ("failed", None): "LBL_SERVICES_ERROR",
    ("failed", True): "LBL_SERVICES_ERROR",
    ("inactive", None): "LBL_SERVICES_STOPPED",
    ("inactive", False): "LBL_SERVICES_DEAD",
}
for (state, live), key in KEYS.items():
    check(f"word for state={state} live={live}", svc._badge_label({"activeState": state, "live": live}), i18n._(key))

for language in [name for name, _label in i18n.AVAILABLE_LANGUAGES]:
    words = i18n.load_language(language)
    keys = sorted(set(KEYS.values()))
    check(f"{language}: every badge word is translated", [k for k in keys if not words.get(k, "").strip()], [])
    check(f"{language}: the badge words differ from each other", len({words[k] for k in keys}), len(keys))

check("every stack has a colour in hex", [k for k, v in svc._STACK_COLOR.items() if not (v.startswith("#") and len(v) == 7)], [])

# --- the handler of the Logs panel ------------------------------------------------------------------------------------------
handler = logging_handler.QtLogHandler()
seen = []
handler.emitter.record_logged.connect(lambda level, name, message: seen.append((level, name, message)))
handler.setFormatter(logging.Formatter("%(message)s"))
record = logging.LogRecord("hydra.test", logging.WARNING, __file__, 1, "link %s", ("lost",), None)
handler.emit(record)
check("one record gives one signal with level, logger and text", seen, [("WARNING", "hydra.test", "link lost")])


class BrokenFormatter(logging.Formatter):
    def format(self, record):
        raise RuntimeError("broken")


handler.setFormatter(BrokenFormatter())
handler.emit(record)
check("a broken formatter falls back to the plain message", seen[-1], ("WARNING", "hydra.test", "link lost"))

first = logging_handler.install()
second = logging_handler.install()
check("installing twice gives the same handler", first is second, True)
root = logging.getLogger()
check("it is attached once", sum(1 for h in root.handlers if isinstance(h, logging_handler.QtLogHandler)), 1)
check("the root level lets information through", root.level != logging.NOTSET and root.level <= logging.INFO, True)
root.removeHandler(first)

print("SERVICE_BADGES_AND_LOG_HANDLER=" + ("PASS" if failures == 0 else f"FAIL {failures}"))
sys.exit(1 if failures else 0)
