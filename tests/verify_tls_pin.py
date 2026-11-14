# =============================================================================
# HYDRA-UMC SUITE - tests/verify_tls_pin.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The pinning of the certificate of a server (net/tls_pin.py), against a real TLS server on this machine:
#   - off by default: the configuration says nothing, or says off, and the default checks are used
#   - the certificate a server shows is read with a bare handshake and its fingerprint is the SHA-256 of the DER form
#   - a pin is refused unless the fingerprint typed is the one of the certificate
#   - with the switch on and a pin, a connection to that address succeeds with exactly that certificate and fails with any
#     other, even one made for the same name; an address without a pin keeps the default checks
#   - a broken configuration section counts as off and empty
# The certificates are made here by the test (the cryptography package, else the openssl program) and thrown away.
# =============================================================================
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, ".")

from hydra_suite.net import tls_pin

failures = 0


def check(label, actual, expected):
    global failures
    ok = actual == expected
    print(("PASS" if ok else "FAIL"), label, "" if ok else f"(got {actual!r}, want {expected!r})")
    if not ok:
        failures += 1


def make_certificate(directory: Path, name: str) -> tuple[Path, Path]:
    cert, key = directory / f"{name}.crt", directory / f"{name}.key"
    try:
        import datetime

        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.x509.oid import NameOID

        private = ec.generate_private_key(ec.SECP256R1())
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
        now = datetime.datetime.now(datetime.timezone.utc)
        built = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(private.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(minutes=5))
            .not_valid_after(now + datetime.timedelta(days=2))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
            .sign(private, hashes.SHA256())
        )
        cert.write_bytes(built.public_bytes(serialization.Encoding.PEM))
        key.write_bytes(private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    except ImportError:
        openssl = shutil.which("openssl")
        if openssl is None:
            print("FAIL neither the cryptography package nor the openssl program is available to make a test certificate")
            sys.exit(1)
        subprocess.run(
            [openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key), "-out", str(cert), "-days", "2", "-subj", "/CN=localhost"],
            check=True,
            capture_output=True,
        )
    return cert, key


class TlsServer:
    """Answers one handshake at a time on a free local port with the given certificate, until closed."""

    def __init__(self, cert: Path, key: Path):
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.context.load_cert_chain(str(cert), str(key))
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(8)
        self.port = self.sock.getsockname()[1]
        self.running = True
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        while self.running:
            try:
                raw, _addr = self.sock.accept()
            except OSError:
                return
            try:
                with self.context.wrap_socket(raw, server_side=True) as tls:
                    tls.recv(1)
            except (OSError, ssl.SSLError):
                pass

    def close(self):
        self.running = False
        self.sock.close()


def connects(context, port) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=5) as raw, context.wrap_socket(raw, server_hostname="127.0.0.1") as tls:
            tls.send(b"x")
        return True
    except (OSError, ssl.SSLError):
        return False


work = Path(tempfile.mkdtemp(prefix="hydra-tls-pin-"))
cert_a, key_a = make_certificate(work, "a")
cert_b, key_b = make_certificate(work, "b")
server_a, server_b = TlsServer(cert_a, key_a), TlsServer(cert_b, key_b)
try:
    check("no section counts as off and empty", tls_pin.read_settings({}), (False, {}))
    check("a section that is not a mapping counts as off", tls_pin.read_settings({"tlsPinning": 5}), (False, {}))
    check("an enabled flag that is not exactly true counts as off", tls_pin.read_settings({"tlsPinning": {"enabled": "yes"}})[0], False)
    check("the key of a server is one spelling", tls_pin.server_key(" Host.Example ", 3000), "host.example:3000")

    pem_a, finger_a = tls_pin.fetch_certificate("127.0.0.1", server_a.port)
    check("the certificate read is the one the server shows", pem_a.strip(), cert_a.read_text(encoding="ascii").strip())
    check("the fingerprint is the SHA-256 of the DER form", finger_a, tls_pin.fingerprint_of_pem(pem_a))
    check("a fingerprint is 32 pairs separated by colons", len(finger_a.split(":")), 32)
    pem_b, finger_b = tls_pin.fetch_certificate("127.0.0.1", server_b.port)
    check("two certificates have two fingerprints", finger_a != finger_b, True)

    config: dict = {}
    refused = False
    try:
        tls_pin.pin_entry(config, "127.0.0.1", server_a.port, pem_a, expected_fingerprint=finger_b)
    except tls_pin.PinError:
        refused = True
    check("a pin is refused when the typed fingerprint is another certificate's", refused, True)
    section = tls_pin.pin_entry(config, "127.0.0.1", server_a.port, pem_a, expected_fingerprint=finger_a.lower().replace(":", " "))
    check("a typed fingerprint is compared without case or separators", sorted(section["servers"]), [f"127.0.0.1:{server_a.port}"])

    off = {"tlsPinning": section}
    check("with the switch off the default checks are used", tls_pin.verify_for(off, "127.0.0.1", server_a.port), True)
    on = {"tlsPinning": tls_pin.with_enabled(off, True)}
    check("with the switch on but no pin for the address, the default checks stay", tls_pin.verify_for(on, "127.0.0.1", server_b.port), True)

    context = tls_pin.verify_for(on, "127.0.0.1", server_a.port)
    check("with the switch on and a pin the context trusts the pinned certificate", isinstance(context, ssl.SSLContext), True)
    check("a connection to the pinned certificate succeeds", connects(context, server_a.port), True)
    check("the default checks refuse a self-signed certificate", connects(ssl.create_default_context(), server_a.port), False)

    # the same address now shows another certificate: refused
    swapped = {"tlsPinning": tls_pin.pin_entry(on, "127.0.0.1", server_b.port, pem_a)}
    swapped["tlsPinning"]["enabled"] = True
    check("another certificate for a pinned address is refused", connects(tls_pin.verify_for(swapped, "127.0.0.1", server_b.port), server_b.port), False)

    gone = {"tlsPinning": tls_pin.unpin_entry(on, "127.0.0.1", server_a.port)}
    check("removing a pin goes back to the default checks", tls_pin.verify_for(gone, "127.0.0.1", server_a.port), True)

    unreadable = False
    try:
        tls_pin.fetch_certificate("127.0.0.1", 1)
    except tls_pin.PinError:
        unreadable = True
    check("a server that cannot be reached is a PinError", unreadable, True)
finally:
    server_a.close()
    server_b.close()
    shutil.rmtree(work, ignore_errors=True)

print("ALL PASS" if failures == 0 else f"{failures} FAILED")
sys.exit(1 if failures else 0)
