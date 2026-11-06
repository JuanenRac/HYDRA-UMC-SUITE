# =============================================================================
# HYDRA-UMC SUITE - tests/verify_developer_node_status.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies the screen of the status of the developer node without any window: how the answer of the server is read (only plain values are
# kept, damaged nodes are dropped), the sentences for a switch that is off or a refused account, and the rows that are shown.
# =============================================================================
import sys

sys.path.insert(0, ".")

from hydra_suite.i18n import _
from hydra_suite.panel_logic import developer_node_status as dev

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


BODY = {
    "nodes": {
        "dev-b": {"at": 1700000000000, "seq": 4, "status": {"version": "1.2.3", "ok": True, "count": 7, "nested": {"a": 1}, "list": [1]}},
        "dev-a": {"at": 1700000001000, "seq": 9, "status": {}},
    },
    "chain": {"ok": True},
}
parsed = dev.parse_status(BODY)
check("the nodes are sorted by id", [n["nodeId"] for n in parsed["nodes"]], ["dev-a", "dev-b"])
check("only plain values are kept", parsed["nodes"][1]["fields"], [{"name": "version", "value": "1.2.3"}, {"name": "ok", "value": "true"}, {"name": "count", "value": "7"}])
check("the chain result is read", parsed["chain"], {"ok": True})
check("an answer without nodes is refused", (dev.parse_status({}), dev.parse_status({"nodes": []}), dev.parse_status(None)), (None, None, None))
check("a node without a time or an entry number is dropped", dev.parse_status({"nodes": {"x": {"at": "now", "seq": 1}, "y": {"at": 1, "seq": True}, "z": 5}})["nodes"], [])
check("a damaged chain result is ignored", dev.parse_status({"nodes": {}, "chain": {"ok": "yes"}})["chain"], None)
check("the fields are limited", len(dev.parse_status({"nodes": {"x": {"at": 1, "seq": 1, "status": {f"k{i}": i for i in range(100)}}}})["nodes"][0]["fields"]), dev.MAX_FIELDS)
check("a long text is cut", len(dev.parse_status({"nodes": {"x": {"at": 1, "seq": 1, "status": {"k": "a" * 1000}}}})["nodes"][0]["fields"][0]["value"]), dev.MAX_TEXT)

check("a switch that is off, a refused account and a failure have their sentence", (dev.status_for((404, {})), dev.status_for((403, {})), dev.status_for(None), dev.status_for((200, {"x": 1})), dev.status_for((200, BODY))), (_("DEVNODE_OFF"), _("DEVNODE_FORBIDDEN"), _("DEVNODE_LOAD_ERROR"), _("DEVNODE_LOAD_ERROR"), ""))
view = dev.view(parsed)
check("the view has a row per node with its time and fields", ([r["title"] for r in view["rows"]], view["rows"][1]["fields"].splitlines()[:2], _("DEVNODE_ENTRY") in view["rows"][0]["received"]), (["dev-a", "dev-b"], ["version: 1.2.3", "ok: true"], True))
check("the chain is said intact or broken", (view["chain"], view["chainOk"], dev.view({"nodes": [], "chain": {"ok": False}})["chain"]), (_("DEVNODE_CHAIN_OK"), True, _("DEVNODE_CHAIN_BROKEN")))
check("no node yet is told, and no answer shows only the problem", (dev.view({"nodes": [], "chain": None})["none"], dev.view(None, "x")), (True, {"problem": "x", "rows": [], "none": False, "chain": "", "chainOk": False}))
for key in ("DEVNODE_TITLE", "DEVNODE_DESC", "DEVNODE_REFRESH", "DEVNODE_VERIFY", "DEVNODE_CHAIN_OK", "DEVNODE_CHAIN_BROKEN", "DEVNODE_NONE", "DEVNODE_OFF", "DEVNODE_LOAD_ERROR", "DEVNODE_FORBIDDEN", "DEVNODE_RECEIVED", "DEVNODE_ENTRY"):
    check(f"sentence {key} exists", _(key) != key, True)

print("FAILURES:", failures)
sys.exit(1 if failures else 0)
