# =============================================================================
# HYDRA-UMC-SUITE - diagnostics bundle verifier
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The support bundle has the report and the client log, lists the servers by
# their public facts only, and never carries a credential: not the password or
# user name of a server entry, and not a token or password that appears inside
# a log line. No Qt window and no network are needed.
# =============================================================================
import io
import sys
import zipfile

sys.path.insert(0, ".")
from hydra_suite import __version__
from hydra_suite.diagnostics import REDACTED, build_bundle, redact


def check(label: str, condition: bool) -> None:
    assert condition, label


def bridge_cases() -> None:
    """The interface writes the bundle with its own log lines and the servers of the list."""
    import asyncio
    import logging
    import tempfile
    from pathlib import Path

    import qasync
    from PySide6.QtGui import QGuiApplication

    from hydra_suite.app import SuiteController
    from qt_suite import SuiteQtBridge

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    asyncio.set_event_loop(qasync.QEventLoop(app))
    controller = SuiteController()
    bridge = SuiteQtBridge(controller)
    bridge.addManualServer("10.1.1.1", 3000, "root", "hunter2", False)
    logging.getLogger("net").warning("refused: token=abc999secret")
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "out.zip"
        bridge.export_diagnostics_to(str(target))
        with zipfile.ZipFile(target) as archive:
            log, report = archive.read("client_log.txt"), archive.read("report.txt")
        check("the log lines are in the bundle", b"refused" in log)
        check("the secrets are not", b"abc999secret" not in log and b"hunter2" not in report and b"root" not in report)
        check("the server is listed", b"10.1.1.1" in report)
        try:
            bridge.export_diagnostics_to(str(Path(folder) / "missing" / "out.zip"))
        except OSError:
            pass
        else:
            raise AssertionError("an unwritable path must raise OSError")
        bridge.exportDiagnostics(str(Path(folder) / "missing" / "again.zip"))
        check("an unwritable path is said to the operator, not raised", bridge.noticeText != "" and bridge.noticeSeverity == "warn")
        good = Path(folder) / "second"
        bridge.exportDiagnostics(good.as_uri())
        check("the bundle is written from a file address", (Path(folder) / "second.zip").is_file())
        check("and the operator is told where", bridge.noticeSeverity == "info" and "second.zip" in bridge.noticeText)


def main() -> None:
    secret_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoiYWRtaW4ifQ.c2lnbmF0dXJlMTIz"
    cases = {
        "password=hunter2 next": "hunter2",
        '{"password": "hunter2", "user": "x"}': "hunter2",
        "Authorization: Bearer abc.def-123": "abc.def-123",
        "GET /ws?token=abc123&x=1": "abc123",
        f"jwt {secret_jwt} end": secret_jwt,
        "refresh_token=zzz999": "zzz999",
        "api-key: K-1234567": "K-1234567",
    }
    for line, secret in cases.items():
        cleaned = redact(line)
        check(f"secret removed from {line!r} -> {cleaned!r}", secret not in cleaned and REDACTED in cleaned)
    check("a harmless line is unchanged", redact("INFO connected to 192.168.0.5:3000") == "INFO connected to 192.168.0.5:3000")

    servers = [
        {"label": "Bench", "host": "192.168.0.180", "port": 3000, "status": "connected", "app_version": "0.8.2.0",
         "remote_api_version": 3, "role": "admin", "username": "root", "password": "hunter2", "token": secret_jwt},
        {"host": "10.0.0.2", "port": 3000},
    ]
    logs = ["12:00:01 INFO hydra_suite.net: login password=hunter2", f"12:00:02 WARNING ws token={secret_jwt}"]
    data = build_bundle(servers, logs)
    archive = zipfile.ZipFile(io.BytesIO(data))
    check("the bundle holds exactly the two files", sorted(archive.namelist()) == ["client_log.txt", "report.txt"])
    report = archive.read("report.txt").decode("utf-8")
    log = archive.read("client_log.txt").decode("utf-8")
    check("the report carries the version", f"HYDRA-UMC SUITE: {__version__}" in report)
    check("the report lists both servers", "Server 1" in report and "Server 2" in report and "192.168.0.180" in report)
    for text in (report, log):
        for secret in ("hunter2", secret_jwt, "root"):
            check(f"{secret[:8]!r} never reaches the bundle", secret not in text)
    check("the log keeps its lines", "login password=" + REDACTED in log)
    check("an empty list is said plainly", "No server in the list." in zipfile.ZipFile(io.BytesIO(build_bundle([], []))).read("report.txt").decode())
    bridge_cases()
    print("verify_diagnostics_bundle: OK")


if __name__ == "__main__":
    main()
