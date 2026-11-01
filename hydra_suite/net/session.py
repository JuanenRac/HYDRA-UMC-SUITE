# =============================================================================
# HYDRA-UMC SUITE - net/session.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The session of one server in one place. Who is signed in, with which token, whether the token can be renewed,
# which role the server gave, whether the credentials were refused and how long the login limiter asks to wait used
# to be loose fields of the connection, changed from half a dozen places. Here they are one object with the rules
# that read them (is this an administrator, may this account save the settings tree, which header goes on a request)
# and the three ways the state changes (a login answer, a refresh answer, a dropped session). Nothing here talks to
# the network: the connection asks the server and hands the answer to this object.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass, field

#: Roles that cannot write the settings tree: the server takes it only from an administrator.
READ_ONLY_TREE_ROLES: frozenset[str] = frozenset({"operator", "viewer"})


@dataclass
class Session:
    token: str | None = None
    #: Opaque token of /api/login, exchanged at /api/refresh for a new access token when the first one expires.
    refresh_token: str | None = None
    #: "admin", "operator" or "viewer" as the server said in its last answer; None before the first one.
    role: str | None = None
    #: None before the first login attempt, then whether the last one worked.
    login_ok: bool | None = None
    #: True once the server refused the credentials (or there are none): retrying them only spends its login limit.
    login_rejected: bool = False
    #: Seconds the login limiter of the server asked to wait; None when it did not.
    login_retry_after_s: float | None = None
    #: The code of the second step, typed for the next sign-in only (a code works once and is never saved).
    totp_code: str = ""
    needs_totp: bool = field(default=False)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def may_edit_settings(self) -> bool:
        """Whether this account may change the global settings. False for an operator or a viewer; unknown roles may, the server decides."""
        return self.role not in READ_ONLY_TREE_ROLES

    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def take_totp_code(self) -> str:
        """The code typed for this sign-in, forgotten at once."""
        code, self.totp_code = self.totp_code, ""
        return code

    # -- the ways the state changes ----------------------------------------------------------------

    def accept_login(self, data: object) -> bool:
        """Takes the answer of /api/login. False (state untouched) when it carries no token."""
        if not isinstance(data, dict):
            return False
        token = data.get("token")
        if not isinstance(token, str) or not token:
            return False
        refresh = data.get("refreshToken")
        self.token = token
        self.refresh_token = refresh if isinstance(refresh, str) and refresh else None
        self.login_rejected = False
        self.login_retry_after_s = None
        self.role = data.get("role") if isinstance(data.get("role"), str) else None
        self.needs_totp = False
        self.login_ok = True
        return True

    def accept_refresh(self, body: object) -> bool:
        """Takes the answer of /api/refresh: the new token, a rotated refresh token and the role when it says one."""
        if not isinstance(body, dict) or not isinstance(body.get("token"), str) or not body["token"]:
            return False
        self.token = body["token"]
        new_refresh = body.get("refreshToken")
        if isinstance(new_refresh, str) and new_refresh:
            self.refresh_token = new_refresh
        if isinstance(body.get("role"), str):
            self.role = body["role"]
        return True

    def reject_login(self, *, needs_totp: bool = False) -> None:
        """The server refused the credentials: nothing more is tried until they change."""
        self.login_rejected = True
        self.needs_totp = needs_totp
        self.login_ok = False

    def fail_login(self, retry_after_s: float | None = None) -> None:
        """A login that failed without a refusal of the credentials (limiter, network); the wait is kept when the server gave one."""
        self.login_ok = False
        if retry_after_s is not None:
            self.login_retry_after_s = retry_after_s

    def drop(self) -> None:
        """The token is gone (expired, refused by the socket): the next request has to renew or sign in again."""
        self.token = None
        self.refresh_token = None

    def drop_access_token(self) -> None:
        """Only the access token is gone; the refresh token may still renew it."""
        self.token = None
