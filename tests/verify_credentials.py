# =============================================================================
# HYDRA-UMC SUITE - tests/verify_credentials.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The servers a person asks the program to remember, with a fake secure store (the real one of the computer is
# never touched):
#   - nothing is remembered unless asked; what is remembered is the address, nickname, user name and TLS, in the
#     configuration, and never the password
#   - the password goes to the secure store, under the name of this program, one per server and account
#   - with no secure store (or one that refuses) the server is still remembered, the password is not, and the
#     program says so
#   - forgetting a server removes its entry and its password; changing the account removes the old password
#   - a damaged configuration never stops the program starting
#   - the interface: the Remember choice when adding a server and when editing its credentials, the badge of each
#     row, removing a server forgets it
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import asyncio
import json
import sys

sys.path.insert(0, ".")

import qasync
from PySide6.QtGui import QGuiApplication

from hydra_suite import credentials
from hydra_suite.app import SuiteController
from hydra_suite.credentials import SERVICE_NAME, CredentialStore, SavedServer, secret_key
from hydra_suite.i18n import _
from hydra_suite.models import ServerInfo
from qt_suite import SuiteQtBridge

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


class FakeSecureStore:
    def __init__(self, refuse=False):
        self.items: dict = {}
        self.refuse = refuse

    def get_password(self, service, username):
        if self.refuse:
            raise RuntimeError("locked")
        return self.items.get((service, username))

    def set_password(self, service, username, password):
        if self.refuse:
            raise RuntimeError("locked")
        self.items[(service, username)] = password

    def delete_password(self, service, username):
        if self.refuse:
            raise RuntimeError("locked")
        self.items.pop((service, username))


class FakeConfig:
    def __init__(self, data=None):
        self.data = dict(data or {})

    def load(self):
        return dict(self.data)

    def save(self, updates):
        self.data.update(updates)
        return True


def make_store(backend, config=None):
    config = config or FakeConfig()
    return CredentialStore(backend, config.load, config.save), config


def info(host="10.0.0.9", port=3000, user="ana", password="hunter2", nickname="Bench", tls=False):
    return ServerInfo(host=host, port=port, hostname=host, nickname=nickname, username=user, password=password, use_tls=tls)


def store_rules():
    backend = FakeSecureStore()
    store, config = make_store(backend)
    check("store: nothing remembered at the start", (store.saved_servers(), store.load_servers()), ([], []))
    check("store: a secure store is available", store.secure_store_available, True)
    check("store: remembering reports that the password was stored", store.remember(info(tls=True)), True)
    saved = store.saved_servers()
    check("store: the entry", [(s.host, s.port, s.username, s.nickname, s.use_tls) for s in saved], [("10.0.0.9", 3000, "ana", "Bench", True)])
    check("store: the password is never in the configuration", "hunter2" in json.dumps(config.data), False)
    check("store: it is in the secure store, under this program's name", backend.items, {(SERVICE_NAME, secret_key("10.0.0.9", 3000, "ana")): "hunter2"})
    loaded = store.load_servers()
    check("store: loading gives the server back with its password", [(i.host, i.port, i.username, i.password, i.nickname, i.use_tls) for i in loaded], [("10.0.0.9", 3000, "ana", "hunter2", "Bench", True)])
    check("store: and knows it is remembered", (store.is_remembered("10.0.0.9", 3000), store.is_remembered("10.0.0.9", 3001)), (True, False))

    store.remember(info(user="bob", password="other"))
    check("store: the same server twice is one entry", len(store.saved_servers()), 1)
    check("store: changing the account removes the old password", backend.items, {(SERVICE_NAME, secret_key("10.0.0.9", 3000, "bob")): "other"})
    store.remember(info(host="10.0.0.10", user="ana", password="third"))
    store.forget("10.0.0.9", 3000)
    check("store: forgetting removes the entry and the password", ([s.host for s in store.saved_servers()], list(backend.items)), (["10.0.0.10"], [(SERVICE_NAME, secret_key("10.0.0.10", 3000, "ana"))]))
    store.forget("203.0.113.1", 1)
    store.forget_all()
    check("store: forgetting everything", (store.saved_servers(), backend.items), ([], {}))


def store_without_secure_store():
    store, config = make_store(None)
    check("no store: said so", store.secure_store_available, False)
    check("no store: the server is remembered, the password is not", (store.remember(info()), [s.host for s in store.saved_servers()], "hunter2" in json.dumps(config.data)), (False, ["10.0.0.9"], False))
    check("no store: it loads without a password", [(i.username, i.password) for i in store.load_servers()], [("ana", "")])
    refusing = FakeSecureStore(refuse=True)
    store, _config = make_store(refusing)
    check("a store that refuses: not stored, no exception", store.remember(info()), False)
    check("a store that refuses: reading gives no password", [i.password for i in store.load_servers()], [""])
    store.forget("10.0.0.9", 3000)
    check("a store that refuses: forgetting still removes the entry", store.saved_servers(), [])


def damaged_configuration():
    config = FakeConfig({"servers": [
        {"host": "10.0.0.1", "port": 3000, "username": "a"},
        {"host": "", "port": 3000},
        {"host": "10.0.0.2", "port": 0},
        {"host": "10.0.0.3", "port": True},
        {"host": "10.0.0.4", "port": 70000},
        "text", None, 7,
        {"host": "10.0.0.1", "port": 3000, "username": "again"},
        {"host": "10.0.0.5", "port": 3001, "username": 5, "nickname": None, "useTls": "yes"},
    ]})
    store, _config = make_store(None, config)
    check("config: only valid entries, once each", [(s.host, s.port, s.username, s.use_tls) for s in store.saved_servers()], [("10.0.0.1", 3000, "a", False), ("10.0.0.5", 3001, "", False)])
    check("config: something that is not a list", make_store(None, FakeConfig({"servers": "x"}))[0].saved_servers(), [])
    check("config: a server with no user has no password to look up", make_store(FakeSecureStore(), FakeConfig())[0].password_for(SavedServer("h", 1)), "")


def real_backend_lookup():
    import builtins

    real_import = builtins.__import__

    def refuse_keyring(name, *args, **kwargs):
        if name == "keyring" or name.startswith("keyring."):
            raise ImportError("no keyring")
        return real_import(name, *args, **kwargs)

    builtins.__import__ = refuse_keyring
    try:
        check("keyring: not installed means no store, not a crash", credentials.keyring_backend(), None)
    finally:
        builtins.__import__ = real_import
    backend = credentials.keyring_backend()
    check("keyring: where installed, a real store or none", backend is None or hasattr(backend, "get_password"), True)


def interface():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    backend = FakeSecureStore()
    store, config = make_store(backend)
    controller = SuiteController()
    bridge = SuiteQtBridge(controller, credential_store=store)

    check("ui: the store is announced", bridge.secureStoreAvailable, True)
    bridge.addManualServer("10.0.0.9", 3000, "ana", "hunter2", False)
    conn_id = bridge.serverRows[0]["connId"]
    check("ui: a server added without the choice is not remembered", (bridge.serverRows[0]["remembered"], store.saved_servers(), backend.items), (False, [], {}))
    check("ui: the credentials dialog says so", bridge.serverCredentials(conn_id)["remember"], False)
    bridge.setServerRemembered(conn_id, True)
    check("ui: remembering it", (bridge.serverRows[0]["remembered"], len(store.saved_servers()), list(backend.items.values())), (True, 1, ["hunter2"]))
    check("ui: the dialog follows", bridge.serverCredentials(conn_id)["remember"], True)
    bridge.saveServerCredentials(conn_id, "ana", "newpass", True)
    check("ui: a new password replaces the stored one", list(backend.items.values()), ["newpass"])
    bridge.saveServerCredentials(conn_id, "ana", "newpass", False)
    check("ui: saving with the choice off forgets the server", (store.saved_servers(), backend.items), ([], {}))
    bridge.setServerRemembered(conn_id, True)
    bridge.setServerRemembered(conn_id, False)
    check("ui: turning the choice off forgets it", (store.saved_servers(), backend.items), ([], {}))
    bridge.setServerRemembered(conn_id, True)
    bridge.removeServer(conn_id)
    check("ui: removing a server forgets it too", (store.saved_servers(), backend.items, bridge.serverRows), ([], {}, []))

    bridge.addManualServer("10.0.0.10", 3000, "ana", "pw", True)
    check("ui: added with the choice on", (len(store.saved_servers()), bridge.noticeText), (1, ""))
    check("ui: the file holds no password", "pw" in json.dumps({k: v for k, v in config.data.items() if k != "x"}).replace("ana", ""), False)
    bridge.removeServer(bridge.serverRows[0]["connId"])

    plain_store, _plain_config = make_store(None)
    plain = SuiteQtBridge(SuiteController(), credential_store=plain_store)
    check("ui: no secure store is announced", plain.secureStoreAvailable, False)
    plain.addManualServer("10.0.0.11", 3000, "ana", "pw", True)
    check("ui: remembering without a store keeps the server and warns about the password", (len(plain_store.saved_servers()), plain.noticeText, plain.noticeSeverity), (1, _("MSG_CREDENTIALS_NOT_STORED"), "warn"))
    bare = SuiteQtBridge(SuiteController())
    check("ui: a bridge with no store at all remembers nothing", (bare.secureStoreAvailable, bare.serverCredentials("x")["remember"]), (False, False))
    bare.addManualServer("10.0.0.12", 3000, "ana", "pw", True)
    check("ui: and still adds the server", len(bare.serverRows), 1)

    startup = FakeSecureStore()
    startup_store, startup_config = make_store(startup)
    startup_store.remember(info(host="10.0.0.20"))
    again, _c = make_store(startup, startup_config)
    restarted = SuiteController()
    for remembered in again.load_servers():
        restarted.add_server(remembered)
    only = next(iter(restarted.connections.values()))
    check("start: a remembered server comes back with its password", (only.info.host, only.info.username, only.info.password), ("10.0.0.20", "ana", "hunter2"))
    for c in list(restarted.connections.values()) + list(controller.connections.values()) + list(plain._controller.connections.values()) + list(bare._controller.connections.values()):
        loop.run_until_complete(c.disconnect())


def main():
    store_rules()
    store_without_secure_store()
    damaged_configuration()
    real_backend_lookup()
    interface()
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
