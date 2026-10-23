# =============================================================================
# HYDRA-UMC SUITE - credentials.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The servers of this program and their passwords, kept between runs only when the operator asks for it.
#
# - A server is remembered only when its "remember" choice is on (off by default). What is remembered is its
#   address, nickname, user name and whether it speaks TLS, in the program's configuration file; never the password.
# - The password goes to the secure store of the operating system (Windows Credential Manager, macOS Keychain,
#   the Secret Service of the Linux desktop) through the keyring library, under the service name of this program.
#   When the computer has no such store the server is still remembered but its password is not, and the program
#   says so; a password is never written to the configuration file.
# - Forgetting a server (or turning its choice off) removes its entry from the file and its password from the
#   secure store.
#
# The secure store is injected, so every rule is tested without touching the real one of the computer.
# =============================================================================
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from hydra_suite.models import ServerInfo

logger = logging.getLogger(__name__)

SERVICE_NAME = "HYDRA-UMC-SUITE"
CONFIG_KEY = "servers"


class SecretBackend(Protocol):
    def get_password(self, service: str, username: str) -> str | None: ...
    def set_password(self, service: str, username: str, password: str) -> None: ...
    def delete_password(self, service: str, username: str) -> None: ...


def secret_key(host: str, port: int, username: str) -> str:
    """The name a password is filed under in the secure store: one per server and account."""
    return f"{username}@{host}:{port}"


def keyring_backend() -> SecretBackend | None:
    """The keyring of this computer when it has a real secure store, otherwise None (the library missing, or only
    its "fail"/"null" placeholders, as on a Linux machine with no desktop session)."""
    try:
        import keyring
        from keyring.backends import fail, null
    except ImportError:
        return None
    try:
        active = keyring.get_keyring()
    except Exception as error:  # a broken backend must not stop the program starting
        logger.warning("the secure store of this computer could not be opened: %s", error)
        return None
    if isinstance(active, (fail.Keyring, null.Keyring)):
        return None
    return keyring  # type: ignore[return-value]


@dataclass
class SavedServer:
    host: str
    port: int
    username: str = ""
    nickname: str = ""
    use_tls: bool = False

    def to_json(self) -> dict:
        return {"host": self.host, "port": self.port, "username": self.username, "nickname": self.nickname, "useTls": self.use_tls}

    @classmethod
    def from_json(cls, raw: object) -> "SavedServer | None":
        if not isinstance(raw, dict):
            return None
        host, port = raw.get("host"), raw.get("port")
        if not isinstance(host, str) or not host.strip() or isinstance(port, bool) or not isinstance(port, int) or not 0 < port < 65536:
            return None
        username = raw.get("username")
        nickname = raw.get("nickname")
        return cls(
            host=host.strip(),
            port=port,
            username=username if isinstance(username, str) else "",
            nickname=nickname if isinstance(nickname, str) else "",
            use_tls=raw.get("useTls") is True,
        )


class CredentialStore:
    """Remembers servers (in the configuration) and their passwords (in the secure store of the computer)."""

    def __init__(self, backend: SecretBackend | None, load_config, save_config):
        self._backend = backend
        self._load_config = load_config
        self._save_config = save_config

    @property
    def secure_store_available(self) -> bool:
        return self._backend is not None

    # --- what is remembered ---

    def saved_servers(self) -> list[SavedServer]:
        raw = self._load_config().get(CONFIG_KEY)
        if not isinstance(raw, list):
            return []
        servers: list[SavedServer] = []
        for item in raw:
            server = SavedServer.from_json(item)
            if server is not None and all((s.host, s.port) != (server.host, server.port) for s in servers):
                servers.append(server)
        return servers

    def is_remembered(self, host: str, port: int) -> bool:
        return any((s.host, s.port) == (host, port) for s in self.saved_servers())

    def remember(self, info: ServerInfo) -> bool:
        """Remembers a server and, when the computer has a secure store, its password. Returns True when the
        password was stored too (False: only the address and user name were, or the store refused it)."""
        servers = [s for s in self.saved_servers() if (s.host, s.port) != (info.host, info.port)]
        previous = next((s for s in self.saved_servers() if (s.host, s.port) == (info.host, info.port)), None)
        servers.append(SavedServer(info.host, info.port, info.username, info.nickname, info.use_tls))
        self._save_config({CONFIG_KEY: [s.to_json() for s in servers]})
        if previous is not None and previous.username and previous.username != info.username:
            self._delete_secret(previous.host, previous.port, previous.username)
        return self._store_password(info)

    def forget(self, host: str, port: int) -> None:
        """Forgets a server: its entry in the file and its password in the secure store."""
        saved = self.saved_servers()
        for server in saved:
            if (server.host, server.port) == (host, port):
                self._delete_secret(server.host, server.port, server.username)
        self._save_config({CONFIG_KEY: [s.to_json() for s in saved if (s.host, s.port) != (host, port)]})

    def forget_all(self) -> None:
        for server in self.saved_servers():
            self._delete_secret(server.host, server.port, server.username)
        self._save_config({CONFIG_KEY: []})

    # --- the password ---

    def password_for(self, server: SavedServer) -> str:
        if self._backend is None or not server.username:
            return ""
        try:
            return self._backend.get_password(SERVICE_NAME, secret_key(server.host, server.port, server.username)) or ""
        except Exception as error:
            logger.warning("the password of %s:%s could not be read from the secure store: %s", server.host, server.port, error)
            return ""

    def load_servers(self) -> list[ServerInfo]:
        """The remembered servers, each with its password when the secure store still has it."""
        return [
            ServerInfo(
                host=s.host,
                port=s.port,
                hostname=s.host,
                nickname=s.nickname,
                username=s.username,
                password=self.password_for(s),
                use_tls=s.use_tls,
            )
            for s in self.saved_servers()
        ]

    def _store_password(self, info: ServerInfo) -> bool:
        if self._backend is None or not info.username or not info.password:
            return False
        try:
            self._backend.set_password(SERVICE_NAME, secret_key(info.host, info.port, info.username), info.password)
            return True
        except Exception as error:
            logger.warning("the password of %s:%s could not be stored: %s", info.host, info.port, error)
            return False

    def _delete_secret(self, host: str, port: int, username: str) -> None:
        if self._backend is None or not username:
            return
        try:
            self._backend.delete_password(SERVICE_NAME, secret_key(host, port, username))
        except Exception as error:  # already gone, or the store is locked: nothing more to do
            logger.info("no password to remove for %s:%s (%s)", host, port, error)
