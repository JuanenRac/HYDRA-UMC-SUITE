# =============================================================================
# HYDRA-UMC-SUITE - translated connection messages verifier
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The messages the connection puts in the status bar (a refused write, a
# command that was not applied, a failed login, a STOP that did not get
# through) come from the language files, not from English literals in the
# code. English keeps its exact wording; every other language is checked by
# switching the active catalog. No Qt window and no network are needed.
# =============================================================================
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hydra_suite import i18n
from hydra_suite.net import client

CLIENT_SOURCE = (ROOT / "hydra_suite" / "net" / "client.py").read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, status: int, body: bytes = b"{}"):
        self.status_code = status
        self._body = body

    def json(self):
        import json

        return json.loads(self._body)


def check(label: str, condition: bool) -> None:
    assert condition, label


def use(language: str) -> None:
    i18n._translations = i18n.load_language(language)


def main() -> None:
    # No emitted message may be an f-string literal any more.
    emitted = re.findall(r"self\.error\.emit\(\s*f?\"", CLIENT_SOURCE)
    check(f"client.py still emits {len(emitted)} message(s) built from a string literal", not emitted)
    check("describe_rejection still builds English text", 'f"{what} rejected' not in CLIENT_SOURCE)

    use("english")
    what = i18n._("MSG_NET_WHAT_STOP")
    check("english 401", client.describe_rejection(FakeResponse(401), what) == "STOP rejected: not authenticated (session expired)")
    check("english 403", client.describe_rejection(FakeResponse(403, b'{"error":"nope"}'), what) == "STOP rejected: permission denied (nope)")
    check("english 409", "reserved by another account (busy)" in client.describe_rejection(FakeResponse(409, b'{"error":"busy"}'), what))
    check("english 500", client.describe_rejection(FakeResponse(500), what) == "STOP failed: HTTP 500")

    use("spanish")
    check("spanish 401", client.describe_rejection(FakeResponse(401), i18n._("MSG_NET_WHAT_WRITE")) == "Escritura: rechazado, no autenticado (sesión caducada)")
    check("spanish 500", client.describe_rejection(FakeResponse(500), i18n._("MSG_NET_WHAT_COMMAND")) == "Comando: error HTTP 500")
    use("german")
    check("german 400", client.describe_rejection(FakeResponse(400, b'{"error":"zu weit"}'), i18n._("MSG_NET_WHAT_COMMAND")) == "Befehl abgelehnt: zu weit")
    use("japanese")
    check("japanese keeps the placeholder filled", "{" not in client.describe_rejection(FakeResponse(403), i18n._("MSG_NET_WHAT_WRITE")))
    use("english")
    print("verify_client_messages_translated: OK")


if __name__ == "__main__":
    main()
