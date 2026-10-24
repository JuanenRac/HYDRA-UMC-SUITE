# =============================================================================
# HYDRA-UMC SUITE - panel_logic/users.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The user accounts screen (administrators only), without any window toolkit: the rows of the table, the checks
# made before anything is sent and the sentences about a refusal. The accounts live on the server (/api/users);
# this module only reads its answers and phrases them in the language of the interface.
# =============================================================================
from __future__ import annotations

from hydra_suite.i18n import _

ROLES = ("operator", "admin")
DEFAULT_ROLE = "operator"

#: The shortest password the server accepts (its own rule; checked here only to save a round trip).
MIN_PASSWORD_LENGTH = 8


def role_label(role: str) -> str:
    return _("USERS_ROLE_ADMIN") if role == "admin" else _("USERS_ROLE_OPERATOR")


def role_options() -> list[dict[str, str]]:
    return [{"value": role, "label": role_label(role)} for role in ROLES]


def parse_users(body: object) -> list[dict[str, str]]:
    """The accounts of GET /api/users, tolerant of damaged entries (an entry that is not an account is skipped)."""
    users = body.get("users") if isinstance(body, dict) else None
    out: list[dict[str, str]] = []
    if not isinstance(users, list):
        return out
    for item in users:
        if not isinstance(item, dict):
            continue
        name = item.get("username")
        if not isinstance(name, str) or not name:
            continue
        role = item.get("role") if item.get("role") in ROLES else DEFAULT_ROLE
        created = item.get("createdAt")
        out.append({"username": name, "role": role, "createdAt": created if isinstance(created, str) else ""})
    return out


def rows(users: list[dict[str, str]], own_username: str = "") -> list[dict[str, object]]:
    """The table: one dict per account, in the order the server gave."""
    return [
        {
            "username": user["username"],
            "role": user["role"],
            "roleLabel": role_label(user["role"]),
            "created": user["createdAt"].replace("T", " ").rsplit(".", 1)[0].rstrip("Z"),
            "own": bool(own_username) and user["username"].lower() == own_username.lower(),
        }
        for user in users
    ]


def check_new(username: str, password: str) -> str:
    """The reason a new account cannot be sent yet, as a sentence; "" when it can."""
    if not username.strip():
        return _("USERS_ERR_USERNAME_REQUIRED")
    if len(password) < MIN_PASSWORD_LENGTH:
        return _("USERS_ERR_PASSWORD_SHORT", count=MIN_PASSWORD_LENGTH)
    return ""


def check_change(username: str, new_username: str, password: str, role: str) -> str:
    """The reason a change cannot be sent yet; "" when it can. `role` is "" when it stays as it is."""
    if not username:
        return _("USERS_ERR_SELECT_ACCOUNT")
    if not new_username.strip() and not password and not role:
        return _("USERS_ERR_NOTHING_TO_CHANGE")
    if password and len(password) < MIN_PASSWORD_LENGTH:
        return _("USERS_ERR_PASSWORD_SHORT", count=MIN_PASSWORD_LENGTH)
    return ""


#: What the server says (its messages are English and fixed) -> the key of the sentence in the interface.
_SERVER_MESSAGES = (
    ("already exists", "USERS_ERR_EXISTS"),
    ("last remaining admin", "USERS_ERR_LAST_ADMIN"),
    ("not found", "USERS_ERR_NOT_FOUND"),
    ("at least", "USERS_ERR_PASSWORD_SHORT"),
    ("required", "USERS_ERR_USERNAME_REQUIRED"),
)


def failure_text(status: int, code: str, detail: str = "") -> str:
    """Why a request about accounts was refused, as a sentence."""
    if code == "network":
        return _("USERS_FAILURE_NETWORK")
    if code == "forbidden":
        return _("USERS_FAILURE_FORBIDDEN")
    if code == "session_expired":
        return _("USERS_FAILURE_SESSION")
    if status == 404 and not detail:
        return _("USERS_FAILURE_UNAVAILABLE")
    lowered = detail.lower()
    for fragment, key in _SERVER_MESSAGES:
        if fragment in lowered:
            return _(key, count=MIN_PASSWORD_LENGTH)
    return _("USERS_FAILURE_OTHER")
