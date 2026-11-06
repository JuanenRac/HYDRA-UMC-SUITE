# =============================================================================
# HYDRA-UMC SUITE - panel_logic/developer_node_status.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The latest status that each developer node sent to the server (GET /api/developer-node/status, read only). The route answers 404 while
# its switch is off (the screen says so) and on a server that predates it. Only plain texts, numbers and yes/no values of the status are
# shown, as text; nothing the node sends is interpreted. Read without any window toolkit.
# =============================================================================
from __future__ import annotations

import time

from hydra_suite.i18n import _

MAX_FIELDS = 24
MAX_TEXT = 200


def parse_status(body: object) -> dict | None:
    """The nodes of an answer, sorted by id; None when the answer has no `nodes` object. A status field that is not text, number or yes/no is left out."""
    if not isinstance(body, dict) or not isinstance(body.get("nodes"), dict):
        return None
    nodes = []
    for node_id, item in body["nodes"].items():
        if not isinstance(item, dict) or isinstance(item.get("at"), bool) or not isinstance(item.get("at"), (int, float)):
            continue
        if isinstance(item.get("seq"), bool) or not isinstance(item.get("seq"), int):
            continue
        fields = []
        status = item.get("status")
        for name, value in (status.items() if isinstance(status, dict) else []):
            if len(fields) >= MAX_FIELDS:
                break
            if isinstance(value, (str, int, float, bool)):
                text = ("true" if value else "false") if isinstance(value, bool) else str(value)
                fields.append({"name": str(name)[:64], "value": text[:MAX_TEXT]})
        nodes.append({"nodeId": str(node_id), "at": item["at"], "seq": item["seq"], "fields": fields})
    nodes.sort(key=lambda n: n["nodeId"])
    chain = body.get("chain")
    return {"nodes": nodes, "chain": {"ok": chain["ok"]} if isinstance(chain, dict) and isinstance(chain.get("ok"), bool) else None}


def status_for(result: tuple[int, object] | None) -> str:
    """The sentence for a failed reading, empty when it worked."""
    if result is None:
        return _("DEVNODE_LOAD_ERROR")
    status, body = result
    if status == 404:
        return _("DEVNODE_OFF")
    if status in (401, 403):
        return _("DEVNODE_FORBIDDEN")
    if status == 200 and parse_status(body) is not None:
        return ""
    return _("DEVNODE_LOAD_ERROR")


def _when(at_ms: float) -> str:
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(at_ms / 1000))
    except (OverflowError, OSError, ValueError):
        return "-"


def view(status: dict | None, problem: str = "") -> dict:
    """What the screen shows: one row per node (title, line with the time and entry, one text of the fields) and the result of the chain check."""
    rows = []
    chain_text = ""
    if status is not None:
        for node in status["nodes"]:
            rows.append(
                {
                    "title": node["nodeId"],
                    "received": f"{_('DEVNODE_RECEIVED')}: {_when(node['at'])} - {_('DEVNODE_ENTRY')} {node['seq']}",
                    "fields": "\n".join(f"{f['name']}: {f['value']}" for f in node["fields"]),
                }
            )
        if status["chain"] is not None:
            chain_text = _("DEVNODE_CHAIN_OK") if status["chain"]["ok"] else _("DEVNODE_CHAIN_BROKEN")
    return {
        "problem": problem,
        "rows": rows,
        "none": status is not None and not rows,
        "chain": chain_text,
        "chainOk": status is not None and status["chain"] is not None and status["chain"]["ok"],
    }
