# =============================================================================
# HYDRA-UMC SUITE - tests/verify_ops_proposals.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies, without any window, the proposals of the node watchdog that wait for a person: how the answer of the server is read, what a
# decision sends (confirm only to approve, never a name), when the screen asks first, when the section is hidden, and the sentences.
# =============================================================================
import sys

sys.path.insert(0, ".")

from hydra_suite.i18n import _
from hydra_suite.panel_logic import ops_proposals as ops

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


INCIDENT = {"incidentId": "inc-1", "sourceNode": "cm5-a", "detectedAt": "t0", "severity": "high", "component": "hydra-umc-server.service", "symptom": "restarting"}
LISTING = {"pending": [{"incident": INCIDENT, "receivedAt": "r"}], "decided": [{"incidentId": "old", "decision": "rejected", "by": "root", "decidedAt": "d"}]}

lists = ops.parse_lists(LISTING)
check("reads the pending proposals", [p["incidentId"] for p in lists["pending"]], ["inc-1"])
check("reads the decided ones", [d["incidentId"] for d in lists["decided"]], ["old"])
check("drops what is not an entry", [p["incidentId"] for p in ops.parse_lists({"pending": [{"incident": INCIDENT}, 5, {"incident": {}}], "decided": [{"incidentId": "x", "decision": "maybe"}]})["pending"]], ["inc-1"])
check("nothing from a damaged answer", (ops.parse_lists({}), ops.parse_lists(None), ops.parse_lists([])), (None, None, None))
check("confirm only to approve", (ops.body_for("a", "approved"), ops.body_for("a", "rejected")), ({"incidentId": "a", "decision": "approved", "confirm": True}, {"incidentId": "a", "decision": "rejected"}))
check("asks only before approving", (ops.needs_confirmation("approved"), ops.needs_confirmation("rejected")), (True, False))
check("hidden when there is no channel", (ops.hidden_for((404, {})), ops.hidden_for((503, {"available": False})), ops.hidden_for((200, LISTING)), ops.hidden_for((403, {})), ops.hidden_for(None)), (True, True, False, False, False))
check("a proposal no longer pending is not a hidden section", (ops.hidden_for((404, {"code": "operation-failed"})), ops.status_for((404, {"code": "operation-failed"}))), (False, _("OPSPROP_NOT_PENDING")))
check("a refused account and a network failure have their own sentence", (ops.status_for((403, {})), ops.status_for(None), ops.status_for((200, LISTING))), (_("OPSPROP_FORBIDDEN"), _("OPSPROP_LOAD_ERROR"), ""))
check("a refusal of the watchdog shows its reason", ops.status_for((502, {"reason": "no file"})), _("OPSPROP_DECIDE_ERROR", reason="no file"))
check("a decision is ok only when the answer names it", (ops.decision_ok((200, {"decision": "approved"}), "approved"), ops.decision_ok((200, {"decision": "rejected"}), "approved"), ops.decision_ok(None, "approved")), (True, False, False))
view = ops.view(lists)
check("the view lists the pending proposals with a title and a meta line", (view["available"], view["none"], view["pending"][0]["title"], view["pending"][0]["meta"]), (True, False, "hydra-umc-server.service", _("OPSPROP_META", id="inc-1", node="cm5-a", severity="high", at="t0")))
check("the view says the last decisions", view["decided"], [_("OPSPROP_DECIDED_REJECTED", id="old", by="root", at="d")])
check("an empty list says there is none", ops.view({"pending": [], "decided": []})["none"], True)
check("no view without the channel", ops.view(None), {"available": False, "pending": [], "decided": [], "none": False})
for key in ("OPSPROP_TITLE", "OPSPROP_DESC", "OPSPROP_NONE", "COMMON_APPROVE", "OPSPROP_REJECT", "OPSPROP_REFRESH", "OPSPROP_APPROVED", "OPSPROP_REJECTED", "OPSPROP_CONFIRM_TITLE", "OPSPROP_CONFIRM_MESSAGE"):
    check(f"sentence {key} exists", _(key) != key, True)

print(f"FAILURES: {failures}")
sys.exit(1 if failures else 0)
