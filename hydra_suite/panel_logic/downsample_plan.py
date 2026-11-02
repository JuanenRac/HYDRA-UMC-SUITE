# =============================================================================
# HYDRA-UMC SUITE - panel_logic/downsample_plan.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The tier plan of the data lake (how long raw points are kept and how they are rolled up), edited from the Telemetry screen:
# durations, the strict checks, the document sent and the reading of the answers. No window toolkit is needed.
#
# The checks are the same, rule by rule, as the ones the data lake makes when it receives a plan (shape, then coherence, then known
# kinds). They are strict: a plan that fails any of them cannot be saved from here. The data lake checks the plan again on its
# side, so this is a quick answer while typing, never the only guard. The data lake has no switch to relax its rules, so the
# screen has none either.
# =============================================================================
from __future__ import annotations

import re

MAX_TIERS = 1000
MAX_FINE_PER_COARSE = 1440
_UNITS = {"s": 1000, "m": 60_000, "h": 3_600_000, "d": 86_400_000, "w": 604_800_000, "y": 31_536_000_000}
MAX_DURATION_MS = 100 * _UNITS["y"]
_DURATION = re.compile(r"^([0-9]+)([smhdwy])$")
CELLS = ("kind", "field", "raw", "bucket", "fineBucket", "rollupRetention", "fineRetention")
_DURATION_CELLS = CELLS[2:]
CODED_FAILURES = (
    "plan_changed", "confirm_delete_required", "delete_not_allowed", "invalid_plan",
    "incoherent_plan", "unknown_kind", "invalid_request", "write_failed",
)


def empty_tier() -> dict[str, str]:
    return {"kind": "", "field": "*", "raw": "", "bucket": "", "fineBucket": "", "rollupRetention": "", "fineRetention": ""}


def parse_duration(text: str) -> int | None:
    """`90s`, `1m`, `1h`, `30d`, `2w`, `5y` or a whole number of milliseconds -> milliseconds; None when it is neither or out of range."""
    value = str(text).strip().lower()
    if re.fullmatch(r"[0-9]+", value):
        ms = int(value)
    else:
        match = _DURATION.match(value)
        if not match:
            return None
        ms = int(match.group(1)) * _UNITS[match.group(2)]
    return ms if 0 < ms <= MAX_DURATION_MS and ms < 2**53 else None


def format_duration(ms: int) -> str:
    """Milliseconds as the shortest exact text (`3600000` -> `1h`)."""
    for unit in ("y", "w", "d", "h", "m", "s"):
        if ms % _UNITS[unit] == 0:
            return f"{ms // _UNITS[unit]}{unit}"
    return str(ms)


def _issue(tier: int | None, key: str | None, code: str, **params) -> dict:
    return {"tier": tier, "key": key, "code": code, "params": params}


def validate_plan(tiers: list[dict[str, str]], known_kinds: list[str] | None) -> list[dict]:
    """Every problem of a draft, in the order the data lake checks them: the shape of each row, then the coherence of the widths and
    the retentions, then the kinds. `known_kinds` None = not known yet (that check is skipped). Empty = a plan the data lake accepts."""
    if not tiers:
        return [_issue(None, None, "no_tiers")]
    if len(tiers) > MAX_TIERS:
        return [_issue(None, None, "too_many_tiers", max=MAX_TIERS)]
    issues: list[dict] = []
    parsed: list[dict[str, int | None]] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(tiers):
        kind, field = str(row.get("kind", "")).strip(), str(row.get("field", "")).strip()
        if not kind:
            issues.append(_issue(index, "kind", "kind_missing"))
        if not field:
            issues.append(_issue(index, "field", "field_missing"))
        if kind == "*" and field not in ("", "*"):
            issues.append(_issue(index, "field", "default_needs_star_field"))
        if kind and field:
            if (kind, field) in seen:
                issues.append(_issue(index, "kind", "duplicate", kind=kind, field=field))
            seen.add((kind, field))
        values: dict[str, int | None] = {}
        for key in _DURATION_CELLS:
            text = str(row.get(key, "")).strip()
            if not text:
                values[key] = None
                if key in ("raw", "bucket"):
                    issues.append(_issue(index, key, "required"))
                continue
            ms = parse_duration(text)
            values[key] = ms
            if ms is None:
                issues.append(_issue(index, key, "bad_duration", value=text))
        parsed.append(values)
        fine, bucket = values["fineBucket"], values["bucket"]
        if fine is not None and bucket is not None:
            if fine >= bucket:
                issues.append(_issue(index, "fineBucket", "fine_not_smaller"))
            elif bucket % fine != 0:
                issues.append(_issue(index, "fineBucket", "fine_not_divisor"))
            elif bucket // fine > MAX_FINE_PER_COARSE:
                issues.append(_issue(index, "fineBucket", "fine_too_many", max=MAX_FINE_PER_COARSE))
        if str(row.get("fineRetention", "")).strip():
            keep, keep_fine = values["rollupRetention"], values["fineRetention"]
            if not str(row.get("fineBucket", "")).strip():
                issues.append(_issue(index, "fineRetention", "fine_retention_needs_fine"))
            elif kind == "*":
                issues.append(_issue(index, "fineRetention", "fine_retention_on_default"))
            elif keep is not None and keep_fine is not None and keep_fine > keep:
                issues.append(_issue(index, "fineRetention", "fine_retention_longer"))
    if issues:
        return issues
    for index, p in enumerate(parsed):
        raw = p["raw"]
        if raw is not None and p["bucket"] is not None and p["bucket"] > raw:
            issues.append(_issue(index, "bucket", "bucket_longer_than_raw"))
        if raw is not None and p["rollupRetention"] is not None and p["rollupRetention"] < raw:
            issues.append(_issue(index, "rollupRetention", "rollup_shorter_than_raw"))
        if raw is not None and p["fineRetention"] is not None and p["fineRetention"] < raw:
            issues.append(_issue(index, "fineRetention", "fine_retention_shorter_than_raw"))
    if issues:
        return issues
    if known_kinds is not None:
        known = set(known_kinds)
        for index, row in enumerate(tiers):
            kind = str(row.get("kind", "")).strip()
            if kind != "*" and kind not in known:
                issues.append(_issue(index, "kind", "unknown_kind", kind=kind))
    return issues


def draft_to_plan(tiers: list[dict[str, str]], delete: bool) -> dict:
    """The document of the data lake: whole numbers of milliseconds stay numbers, a duration with a unit is sent as typed."""
    out = []
    for row in tiers:
        item: dict[str, object] = {"kind": str(row.get("kind", "")).strip(), "field": str(row.get("field", "")).strip()}
        for key in _DURATION_CELLS:
            text = str(row.get(key, "")).strip().lower()
            if text:
                item[key] = int(text) if re.fullmatch(r"[0-9]+", text) else text
        out.append(item)
    return {"tiers": out, "delete": bool(delete)}


def plan_to_draft(plan) -> tuple[list[dict[str, str]], bool] | None:
    """The rows and the delete flag of a plan document as the data lake stores it; None when it is not one."""
    if not isinstance(plan, dict) or not isinstance(plan.get("tiers"), list):
        return None
    rows = []
    for item in plan["tiers"]:
        if not isinstance(item, dict) or not isinstance(item.get("kind"), str):
            return None
        row = empty_tier()
        row["kind"] = item["kind"]
        row["field"] = item["field"] if isinstance(item.get("field"), str) else "*"
        for key in _DURATION_CELLS:
            value = item.get(key)
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)) and value == value:
                row[key] = format_duration(int(value))
            elif isinstance(value, str):
                row[key] = value
        rows.append(row)
    return rows, plan.get("delete") is True


def failure_for(status: int, body) -> str:
    """The kind of failure of an answer that is not a success, chosen by the `code` of the data lake and never by its text."""
    code = body.get("code") if isinstance(body, dict) else None
    if code in CODED_FAILURES:
        return code
    if status == 404:
        return "off"
    if status in (401, 403):
        return "forbidden"
    if status == 503:
        return "unreachable"
    return "http"


def failure_details(body) -> list[str]:
    details = body.get("details") if isinstance(body, dict) else None
    return [d for d in details if isinstance(d, str)][:50] if isinstance(details, list) else []


def read_plan(body) -> dict | None:
    """The state from the answer of GET: rows, delete flag, hash, known kinds, switches and the latest audit entries; None when malformed."""
    if not isinstance(body, dict) or not isinstance(body.get("hash"), str):
        return None
    draft = plan_to_draft(body.get("plan"))
    if draft is None:
        return None
    rows, delete = draft
    switches = body.get("switches") if isinstance(body.get("switches"), dict) else {}
    audit = [
        {
            "atMs": e.get("atMs") if isinstance(e.get("atMs"), (int, float)) else 0,
            "event": e.get("event") if isinstance(e.get("event"), str) else "",
            "client": e.get("client") if isinstance(e.get("client"), str) else "",
            "tiers": e.get("tiers") if isinstance(e.get("tiers"), int) else 0,
        }
        for e in (body.get("audit") if isinstance(body.get("audit"), list) else [])
        if isinstance(e, dict)
    ][-10:]
    return {
        "rows": rows,
        "delete": delete,
        "hash": body["hash"],
        "knownKinds": [k for k in body.get("knownKinds", []) if isinstance(k, str)] if isinstance(body.get("knownKinds"), list) else [],
        "allowDelete": switches.get("allowDelete") is True,
        "mode": "delete" if switches.get("effectiveMode") == "delete" else "dryRun",
        "fineRollups": switches.get("fineRollups") is not False,
        "audit": audit,
    }


def read_effects(body) -> dict | None:
    """The totals of the effects of a preview or a save: raw points to roll up, rollups and narrow rollups to expire; the count of changes."""
    if not isinstance(body, dict) or not isinstance(body.get("hash"), str):
        return None
    totals = body.get("effects", {}).get("totals") if isinstance(body.get("effects"), dict) else None
    totals = totals if isinstance(totals, dict) else None

    def number(key: str) -> int:
        value = totals.get(key) if totals else 0
        return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0

    return {
        "saved": body.get("saved") is True,
        "hash": body["hash"],
        "changes": len(body["changes"]) if isinstance(body.get("changes"), list) else 0,
        "hasTotals": totals is not None,
        "raw": number("rawPointsToRollUp"),
        "rollups": number("rollupsToExpire"),
        "fine": number("fineRollupsToExpire"),
    }
