# =============================================================================
# HYDRA-UMC SUITE - tests/verify_tool_arms.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies, without any window, the read-only panel of the arm state of the URTC tools: how the answer is checked against the closed contract,
# that an old report is never shown as safe, the order of the rows, the sentence of each kind of failure, the empty and the unavailable
# states, and that every sentence exists in all eight languages with the same placeholders.
# =============================================================================
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")

from hydra_suite.i18n import _
from hydra_suite.panel_logic import tool_arms as ta

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def arm(**over):
    base = {"robot": "arm1", "toolId": 1, "armed": False, "by": "urtc", "seq": 1, "ageSeconds": 2, "stale": False}
    base.update(over)
    return base


def report(rows=None, **over):
    arms = [arm()] if rows is None else rows
    base = {"schema_version": "1.0", "ttlSeconds": 10, "arms": arms, "armedCount": sum(1 for a in arms if isinstance(a, dict) and a["armed"] and not a["stale"]), "staleCount": sum(1 for a in arms if isinstance(a, dict) and a["stale"])}
    base.update(over)
    return base


good = ta.parse_report(report([arm(armed=True), arm(robot="arm2", toolId=24, armed=True, stale=True)]))
check("reads a report of the contract", (good["armedCount"], good["staleCount"], len(good["arms"]), good["ttlSeconds"]), (1, 1, 2, 10.0))

BAD = {
    "another version of the contract": report([], schema_version="2.0"),
    "a ttl of zero": report([], ttlSeconds=0),
    "a ttl that is not a number": report([], ttlSeconds="10"),
    "a ttl that is a boolean": report([], ttlSeconds=True),
    "a negative count": report([], armedCount=-1),
    "a count with decimals": report([], staleCount=1.5),
    "a count that is a boolean": report([], armedCount=True),
    "arms that are not a list": report([], arms={}),
    "a robot id with a space": report([arm(robot="arm 1")]),
    "a robot id that starts with a dot": report([arm(robot=".arm")]),
    "a robot id of 65 characters": report([arm(robot="a" * 65)]),
    "an empty robot id": report([arm(robot="")]),
    "a tool above 24": report([arm(toolId=25)]),
    "a negative tool": report([arm(toolId=-1)]),
    "a tool that is a boolean": report([arm(toolId=True)]),
    "an armed flag that is not a boolean": report([arm(armed="yes")]),
    "a stale flag that is a number": report([arm(stale=1)]),
    "a long reporter": report([arm(by="x" * 65)]),
    "a reporter that is not text": report([arm(by=3)]),
    "a sequence of zero": report([arm(seq=0)]),
    "a negative age": report([arm(ageSeconds=-1)]),
    "an age that is not finite": report([arm(ageSeconds=float("inf"))]),
    "an age that is not a number": report([arm(ageSeconds="2")]),
    "a row that is not an object": report([["arm1"]]),
}
for name, body in BAD.items():
    check(f"refuses {name}", ta.parse_report(body), None)
for bad in (None, 3, "text", [], True):
    check(f"refuses {bad!r}", ta.parse_report(bad), None)
many = lambda n: [arm(robot=f"r{i}") for i in range(n)]
check("accepts exactly 256 arms and refuses 257", (ta.parse_report(report(many(256))) is not None, ta.parse_report(report(many(257)))), (True, None))
check("accepts the longest robot id and the highest tool", ta.parse_report(report([arm(robot="a" * 64, toolId=24)])) is not None, True)

check("an old report is never safe", (ta.level_of(arm(armed=True)), ta.level_of(arm()), ta.level_of(arm(armed=True, stale=True)), ta.level_of(arm(stale=True))), ("armed", "disarmed", "warning", "unknown"))
rows = [arm(robot="b", toolId=2), arm(robot="a", toolId=3, armed=True), arm(robot="a", toolId=1, stale=True), arm(robot="c", toolId=0, armed=True, stale=True)]
before = [dict(r) for r in rows]
check("dangerous rows first, then by robot and tool", [f"{r['robot']}{r['toolId']}" for r in ta.sorted_arms(rows)], ["c0", "a3", "a1", "b2"])
check("sorting does not change its input", rows, before)
check("the age gets the right unit", [ta.age_parts(x) for x in (0, 59.9, 60, 3599, 3600, 86400)], [("s", 0), ("s", 59), ("min", 1), ("min", 59), ("h", 1), ("h", 24)])

check("hidden only for a server that predates the route", (ta.hidden_for((404, {})), ta.hidden_for((200, {})), ta.hidden_for((503, {})), ta.hidden_for(None)), (True, False, False, False))
check("each failure has its own sentence", (ta.status_for(None), ta.status_for((403, {})), ta.status_for((401, {})), ta.status_for((503, {})), ta.status_for((404, {})), ta.status_for((500, {})), ta.status_for((200, {"schema_version": "1.0"})), ta.status_for((200, report()))),
      (_("TOOLARMS_LOAD_ERROR"), _("TOOLARMS_FORBIDDEN"), _("TOOLARMS_FORBIDDEN"), _("TOOLARMS_UNAVAILABLE"), _("TOOLARMS_UNAVAILABLE"), _("TOOLARMS_LOAD_ERROR"), _("TOOLARMS_LOAD_ERROR"), ""))
check("the unavailable sentence differs from a failed reading", _("TOOLARMS_UNAVAILABLE") != _("TOOLARMS_LOAD_ERROR"), True)

view = ta.view(good)
check("the view lists the dangerous row first with its words", (view["available"], view["rows"][0]["level"], _("TOOLARMS_LEVEL_WARNING") in view["rows"][0]["text"], "arm2" in view["rows"][0]["text"]), (True, "warning", True, True))
check("the summary counts the armed and the old reports", ("1" in view["summary"], "10" in view["summary"]), (True, True))
check("a report with no tool says so", (ta.view(ta.parse_report(report([])))["empty"], ta.view(ta.parse_report(report([])))["rows"]), (_("TOOLARMS_EMPTY"), []))
none = ta.view(None)
check("no view without a report, but every key is there for the screen to bind to", (none["available"], sorted(none) == sorted(view)), (False, True))
check("a row without a reporter leaves the reporter out", _("TOOLARMS_BY", by="x") not in ta.view(ta.parse_report(report([arm(by="")])))["rows"][0]["text"], True)

KEYS = ["TITLE", "REFRESH", "DESC", "UNAVAILABLE", "FORBIDDEN", "LOAD_ERROR", "SUMMARY", "EMPTY", "TOOL", "LEVEL_ARMED", "LEVEL_WARNING", "LEVEL_UNKNOWN", "LEVEL_DISARMED", "AGE", "UNIT_S", "UNIT_MIN", "UNIT_H", "BY", "STALE_NOTE"]
for key in KEYS:
    check(f"sentence TOOLARMS_{key} exists", _(f"TOOLARMS_{key}") != f"TOOLARMS_{key}", True)

holes = lambda text: sorted(re.findall(r"\{\w+\}", text))
english = {}
for path in sorted(Path("language").glob("*.lng"), key=lambda p: (p.name != "english.lng", p.name)):
    text = path.read_text(encoding="utf-8")
    values = {}
    for key in KEYS:
        found = re.search(rf"^TOOLARMS_{key}=(.*)$", text, re.M)
        values[key] = found.group(1).strip() if found else None
    check(f"{path.name} has every sentence", [k for k, v in values.items() if not v], [])
    if path.name == "english.lng":
        english = values
    else:
        check(f"{path.name} keeps the placeholders of English", [k for k in KEYS if values[k] and holes(values[k]) != holes(english.get(k) or "")], [])
        check(f"{path.name} translates the sentences that decide what the operator does", [k for k in ("TITLE", "DESC", "LEVEL_WARNING", "LEVEL_UNKNOWN", "STALE_NOTE") if values[k] == english.get(k)], [])

print(f"FAILURES: {failures}")
sys.exit(1 if failures else 0)
