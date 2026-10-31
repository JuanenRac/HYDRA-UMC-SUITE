# =============================================================================
# HYDRA-UMC-SUITE - tests/verify_mesh_pack.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The mesh package: the pinned manifest tells the truth about the meshes of the
# tree; the default source never touches the network; a package is installed
# only when its SHA-256 and the SHA-256 of every file match; a tampered,
# oversized or path-escaping package installs nothing; only https (or loopback
# http) addresses are accepted. The download runs against a local server on
# 127.0.0.1 serving a small package built here in the same format. No Qt, no
# outside network.
# =============================================================================
import gzip
import hashlib
import http.server
import io
import json
import re
import shutil
import sys
import tarfile
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, ".")

from hydra_suite import mesh_pack as mp

failures = 0


def check(label: str, ok: bool) -> None:
    global failures
    print(("PASS " if ok else "FAIL ") + label)
    if not ok:
        failures += 1


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_package(blobs: dict[str, bytes], extra_names: list[tuple[str, bytes]] | None = None) -> bytes:
    raw = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT) as tar:
            for digest, data in sorted(blobs.items()):
                info = tarfile.TarInfo(f"blobs/{digest}")
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            for name, data in extra_names or []:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    return raw.getvalue()


class Server:
    def __init__(self, payload: bytes) -> None:
        outer = self
        self.hits = 0
        self.payload = payload

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                outer.hits += 1
                self.send_response(200)
                self.send_header("Content-Length", str(len(outer.payload)))
                self.end_headers()
                self.wfile.write(outer.payload)

            def log_message(self, *_args):
                pass

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/pack.tgz"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


def run() -> None:
    # ---- the real manifest tells the truth about the tree --------------------------------------------
    manifest = mp.load_manifest()
    files = manifest["files"]
    check("manifest has files", len(files) > 100 and manifest["pack"]["size"] > 0)
    check("manifest paths are sorted and unique", [f["path"] for f in files] == sorted({f["path"] for f in files}))
    # a file that is present must be the pinned one; the missing ones are brought by `ensure` (the runners call it first)
    wrong = [e for e in mp.scan(manifest, deep=True) if (mp.MESH_DIR / e["path"]).exists()]
    check("every mesh of the tree that is present matches the manifest by SHA-256", wrong == [])
    config = mp.load_settings(env={})
    check("default source is auto (the tree does not carry the meshes)", config.source == "auto")
    check("default cache is outside the repository", mp.default_cache_dir() not in mp.ROOT.parents and mp.ROOT not in mp.default_cache_dir().parents)
    check("package address is https", manifest["pack"]["url"].startswith("https://"))

    # ---- messages: eight languages, same keys and placeholders -----------------------------------------
    check("eight languages", sorted(mp.MESSAGES) == ["de", "en", "es", "fr", "it", "ja", "pt", "zh"])
    ph = lambda s: sorted(re.findall(r"\{[a-z_]+\}", s))  # noqa: E731
    ok = all(
        set(t) == set(mp.MESSAGES["en"]) and all(ph(t[k]) == ph(mp.MESSAGES["en"][k]) for k in t)
        for t in mp.MESSAGES.values()
    )
    check("every language has the same keys and placeholders", ok)
    check("Portuguese is European", "transfere" in mp.MESSAGES["pt"]["local"])
    check("language from LANG", mp.language_code({"LANG": "pt_PT.UTF-8"}) == "pt" and mp.language_code({"LANG": "xx"}) == "en")

    # ---- settings: file, environment, damaged file -----------------------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        cfg = tmp_path / "cfg.json"
        cfg.write_text('{"source": "auto", "url": "https://example.invalid/p.tgz"}', encoding="utf-8")
        s = mp.load_settings(cfg, env={})
        check("settings read from the file", s.source == "auto" and s.url.endswith("p.tgz"))
        s = mp.load_settings(cfg, env={"HYDRA_UMC_MESH_SOURCE": "download", "HYDRA_UMC_MESH_URL": "https://e.invalid/x",
                                       "HYDRA_UMC_MESH_CACHE": "/c", "HYDRA_UMC_MESH_PACKAGE": "/p.tgz"})
        check("environment overrides the file", s.source == "download" and s.url == "https://e.invalid/x")
        check("cache folder and package path come from the environment", s.cache == "/c" and s.package == "/p.tgz")
        cfg.write_text("not json", encoding="utf-8")
        check("damaged file falls back to the default (auto)", mp.load_settings(cfg, env={}).source == "auto")

        # ---- a small package and a manifest for it ---------------------------------------------------------
        a, b = b"solid a\n" * 50, b"glTF-b" * 80
        blobs = {sha(a): a, sha(b): b}
        entries = [
            {"path": "robots/x/a.stl", "sha256": sha(a), "size": len(a)},
            {"path": "robots/y/a.stl", "sha256": sha(a), "size": len(a)},
            {"path": "machine/b.glb", "sha256": sha(b), "size": len(b)},
        ]
        package = make_package(blobs)

        def write_manifest(payload: bytes, files_=entries) -> Path:
            path = tmp_path / "meshes.pack.json"
            path.write_text(json.dumps({"schema": 1, "pack": {"file": "p.tgz", "url": "", "sha256": sha(payload), "size": len(payload)}, "files": files_}), encoding="utf-8")
            return path

        manifest_path = write_manifest(package)
        mesh_dir = tmp_path / "meshes"
        cache_dir = tmp_path / "cache"

        def S(**kw) -> mp.Settings:  # noqa: N802 - every Settings of these checks keeps its cache inside the temporary folder
            kw.setdefault("cache", str(cache_dir))
            return mp.Settings(**kw)

        server = Server(package)
        logs: list[str] = []
        try:
            # local: nothing downloaded, nothing written
            n = mp.ensure(S(source="local", url=server.url), manifest_path, mesh_dir, log=logs.append, lang="en")
            check("local never touches the network or the disk", n == 0 and server.hits == 0 and not mesh_dir.exists())

            # auto with an empty folder: downloads and writes all three paths (one blob used twice)
            n = mp.ensure(S(source="auto", url=server.url), manifest_path, mesh_dir, log=logs.append, lang="en")
            check("auto installs the missing meshes", n == 3 and (mesh_dir / "robots/y/a.stl").read_bytes() == a and (mesh_dir / "machine/b.glb").read_bytes() == b)
            check("one download", server.hits == 1)

            # auto with everything present: no network
            n = mp.ensure(S(source="auto", url=server.url), manifest_path, mesh_dir, log=logs.append, lang="en")
            check("auto uses the local meshes when all exist", n == 0 and server.hits == 1)

            # auto keeps a same-size local file it did not verify (quick scan), download mode repairs it
            (mesh_dir / "machine/b.glb").write_bytes(b"x" * len(b))
            n = mp.ensure(S(source="auto", url=server.url), manifest_path, mesh_dir, log=logs.append, lang="en")
            check("auto trusts present files of the right size", n == 0 and server.hits == 1)
            n = mp.ensure(S(source="download", url=server.url), manifest_path, mesh_dir, log=logs.append, lang="en")
            check("download mode replaces only the file whose hash is wrong", n == 1 and (mesh_dir / "machine/b.glb").read_bytes() == b and server.hits == 1)  # the cached package serves the repair

            # a deleted file is fetched again in auto
            (mesh_dir / "robots/x/a.stl").unlink()
            n = mp.ensure(S(source="auto", url=server.url), manifest_path, mesh_dir, log=logs.append, lang="en")
            check("auto brings back a deleted mesh", n == 1 and (mesh_dir / "robots/x/a.stl").is_file())
            check("no .part files are left behind", not list(mesh_dir.rglob("*.part")))
            check("messages are produced", any("Installed" in line for line in logs))

            # the package stays in the cache and is reused without the network
            check("the downloaded package is kept in the cache", (cache_dir / "p.tgz").is_file() and not list(cache_dir.glob("*.part")))
            hits = server.hits
            shutil.rmtree(mesh_dir)
            logs.clear()
            n = mp.ensure(S(source="auto", url=server.url), manifest_path, mesh_dir, log=logs.append, lang="en")
            check("a cached package is reused with no new download", n == 3 and server.hits == hits and any("already stored" in m for m in logs))
            # a damaged cached package is thrown away and fetched again
            (cache_dir / "p.tgz").write_bytes(b"junk")
            shutil.rmtree(mesh_dir)
            n = mp.ensure(S(source="auto", url=server.url), manifest_path, mesh_dir, log=lambda _m: None, lang="en")
            check("a damaged cached package is downloaded again", n == 3 and server.hits == hits + 1 and mp.package_matches(cache_dir / "p.tgz", json.loads(manifest_path.read_text())["pack"]))
        finally:
            server.close()

        # ---- offline: a package file given by path, a dead address, a clear hint -----------------------------
        given = tmp_path / "given.tgz"
        given.write_bytes(package)
        off_dir = tmp_path / "offline_meshes"
        n = mp.ensure(S(source="auto", url="http://127.0.0.1:9/none.tgz", package=str(given), cache=str(tmp_path / "nocache")),
                      manifest_path, off_dir, log=lambda _m: None, lang="en")
        check("a package given by path installs with no network and no cache", n == 3 and not (tmp_path / "nocache").exists())
        given.write_bytes(package + b"0")
        try:
            mp.ensure(S(source="auto", package=str(given)), manifest_path, tmp_path / "off2", log=lambda _m: None)
            check("a wrong package file is refused", False)
        except mp.MeshPackError as exc:
            check("a wrong package file is refused", exc.key == "package_file_bad" and not (tmp_path / "off2").exists())
        try:
            mp.ensure(S(source="auto", package=str(tmp_path / "missing.tgz")), manifest_path, tmp_path / "off3", log=lambda _m: None)
            check("a missing package file is refused", False)
        except mp.MeshPackError as exc:
            check("a missing package file is refused", exc.key == "package_file_bad")
        try:
            mp.ensure(S(source="auto", url="http://127.0.0.1:9/none.tgz", cache=str(tmp_path / "empty_cache")), manifest_path, tmp_path / "off4", log=lambda _m: None)
            check("no network and no cache fails with the way out", False)
        except mp.MeshPackError as exc:
            check("no network and no cache fails with the way out", exc.key == "failed" and {"file", "url", "cache"} <= set(exc.fields)
                  and "HYDRA_UMC_MESH_PACKAGE" in mp.say("hint_network", "en", **exc.fields))
        check("nothing half-written is left in the cache", not list((tmp_path / "empty_cache").glob("*.part")))

        # ---- refusals install nothing ----------------------------------------------------------------------
        def refused(payload: bytes, manifest_sha_of: bytes | None = None, files_=entries, expect: str = "package_bad") -> bool:
            fresh = tmp_path / f"fresh_{sha(payload)[:8]}_{len(files_)}"
            srv = Server(payload)
            try:
                man = write_manifest(manifest_sha_of if manifest_sha_of is not None else payload, files_)
                try:
                    mp.ensure(S(source="auto", url=srv.url, cache=str(fresh) + "_cache"), man, fresh, log=lambda _m: None)
                except mp.MeshPackError as exc:
                    return exc.key == expect and not fresh.exists()
                return False
            finally:
                srv.close()

        check("a package with another hash installs nothing", refused(make_package({sha(a): a}), manifest_sha_of=package))
        tampered = make_package({sha(a): a + b"!", sha(b): b})
        # the manifest pins the tampered package itself (so the whole-package hash passes), but the blob hash must still fail
        check("a blob that does not match its name installs nothing", refused(tampered))
        check("an entry outside blobs/ installs nothing", refused(make_package(blobs, [("../evil", b"x")])))
        check("a package that lacks a wanted blob installs nothing", refused(make_package({sha(a): a})))
        big = package + b"0" * 10
        srv = Server(big)
        try:
            man = write_manifest(package)
            try:
                mp.ensure(S(source="auto", url=srv.url, cache=str(tmp_path / "big_cache")), man, tmp_path / "big", log=lambda _m: None)
                check("an oversized answer is refused", False)
            except mp.MeshPackError as exc:
                check("an oversized answer is refused", exc.key == "package_bad" and not (tmp_path / "big").exists())
        finally:
            srv.close()

        bad_paths = [{"path": "../outside.stl", "sha256": sha(a), "size": len(a)}]
        try:
            write_manifest(package, bad_paths)
            mp.load_manifest(tmp_path / "meshes.pack.json")
            check("a manifest path with .. is rejected", False)
        except mp.MeshPackError:
            check("a manifest path with .. is rejected", True)
        write_manifest(package)

        for url in ("http://example.com/p.tgz", "ftp://127.0.0.1/p.tgz", "file:///etc/passwd"):
            try:
                mp.ensure(S(source="auto", url=url, cache=str(tmp_path / "ins_cache")), manifest_path, tmp_path / "ins", log=lambda _m: None)
                check(f"{url} is refused", False)
            except mp.MeshPackError as exc:
                check(f"{url} is refused", exc.key == "insecure")
        try:
            mp.ensure(S(source="sometimes"), manifest_path, tmp_path / "m", log=lambda _m: None)
            check("an unknown source is refused", False)
        except mp.MeshPackError as exc:
            check("an unknown source is refused", exc.key == "bad_source")
        try:
            mp.ensure(S(source="auto", url="", cache=str(tmp_path / "nu_cache")), write_manifest(package), tmp_path / "nu", log=lambda _m: None)
            check("no address is a clear refusal", False)
        except mp.MeshPackError as exc:
            check("no address is a clear refusal", exc.key == "no_url")
        check("every message renders in every language", all(
            mp.say(k, lang, count=1, size="1", url="u", reason="r", names="n", value="v", error="e", path="p", file="f", cache="c")
            for lang in mp.MESSAGES for k in mp.MESSAGES["en"]
        ))


run()

print()
if failures:
    print(f"FAILED: {failures} mismatches")
    sys.exit(1)
print("ALL VERIFY_MESH_PACK CHECKS PASSED")
