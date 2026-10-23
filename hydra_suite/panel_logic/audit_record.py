# =============================================================================
# HYDRA-UMC SUITE - panel_logic/audit_record.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The audit record screen (administrators only), without any window toolkit: the rows of the table, the labels of
# the filters and the sentences about the chain check. The record itself is read and checked in access.py.
# =============================================================================
from __future__ import annotations

from hydra_suite import access
from hydra_suite.i18n import _

#: The sizes of the window of lines the screen offers (the server gives 1 to 1000).
LIMITS = (50, 100, 250, 1000)
DEFAULT_LIMIT = 100


def type_label(kind: str) -> str:
    """The name of a type of entry in the user's language (the type itself when the interface has no name for it)."""
    key = "AUDIT_TYPE_" + kind.replace("-", "_").upper()
    text = _(key)
    return kind if text == key else text


def outcome_label(outcome: str) -> str:
    key = "AUDIT_OUTCOME_" + outcome.upper()
    text = _(key)
    return outcome if text == key else text


def type_options() -> list[dict[str, str]]:
    return [{"value": "", "label": _("AUDIT_ALL_TYPES")}] + [{"value": kind, "label": type_label(kind)} for kind in access.AUDIT_TYPES]


def rows(entries: list[access.AuditEntry], robot_names: dict[int, str]) -> list[dict[str, object]]:
    """The table: the newest line first, one dict per line."""
    out: list[dict[str, object]] = []
    for entry in reversed(entries):
        out.append(
            {
                "seq": entry.seq,
                "time": entry.ts.replace("T", " ").rsplit(".", 1)[0].rstrip("Z"),
                "type": type_label(entry.type),
                "outcome": outcome_label(entry.outcome),
                "outcomeKind": entry.outcome,
                "account": entry.username or "-",
                "controller": entry.controller_id or "-",
                "address": entry.ip or "-",
                "robot": "-" if entry.robot_id is None else robot_names.get(entry.robot_id, f"#{entry.robot_id}"),
                "detail": access.detail_line(entry.detail),
            }
        )
    return out


def chain_lines(read: access.AuditRead) -> list[dict[str, object]]:
    """The sentences about the chain: what the server said over the whole record (when asked) and what this
    program found in the lines it was given. Each is {text, ok}."""
    lines: list[dict[str, object]] = []
    verification = read.verification
    if verification is not None:
        if verification.get("ok") is True:
            lines.append({"text": _("AUDIT_SERVER_OK", count=verification.get("entries", 0)), "ok": True})
        else:
            lines.append(
                {
                    "text": _("AUDIT_SERVER_BROKEN", seq=verification.get("brokenAtSeq", "?"), reason=verification.get("reason") or ""),
                    "ok": False,
                }
            )
    local = access.check_chain(read.entries)
    if local.ok:
        lines.append({"text": _("AUDIT_LOCAL_OK", count=local.checked, links=local.links, gaps=local.gaps), "ok": True})
    else:
        key = "AUDIT_LOCAL_BROKEN_LINK" if local.reason == "link" else "AUDIT_LOCAL_BROKEN_CHANGED"
        lines.append({"text": _(key, seq=local.broken_at_seq if local.broken_at_seq is not None else "?"), "ok": False})
    return lines


def failure_text(status: int, code: str) -> str:
    """Why the record could not be read, as a sentence."""
    if code == "network":
        return _("AUDIT_FAILURE_NETWORK")
    if code == "forbidden":
        return _("AUDIT_FAILURE_FORBIDDEN")
    if code == "session_expired":
        return _("AUDIT_FAILURE_SESSION")
    if status == 404:
        return _("AUDIT_FAILURE_UNAVAILABLE")
    return _("AUDIT_FAILURE_OTHER")
