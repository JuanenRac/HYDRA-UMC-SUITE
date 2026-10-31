# =============================================================================
# HYDRA-UMC SUITE - mesh_pack.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The 3D models (STL/GLB/AMF/3MF) can come from the working tree (default) or
# from ONE downloadable package whose SHA-256 and the SHA-256 of every file
# are pinned in meshes.pack.json inside this repository. Nothing the package
# holds is trusted until its hash matches the manifest; nothing is written
# outside the mesh folder; a failed check installs nothing.
#
#   source = local     (default) never touches the network; the meshes of the tree are used.
#   source = auto      the local meshes are used when all are present; only the missing or
#                      changed ones are fetched from the package.
#   source = download  every mesh is verified by its hash and the wrong ones are replaced.
#
# Set it in mesh_pack.config.json or with HYDRA_UMC_MESH_SOURCE / HYDRA_UMC_MESH_URL.
# CLI: python -m hydra_suite.mesh_pack status | check | prepare | ensure [--source auto|download]
# Standard library only.
# =============================================================================
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
MESH_DIR = ROOT / "assets" / "meshes"
MANIFEST_PATH = ROOT / "meshes.pack.json"
CONFIG_PATH = ROOT / "mesh_pack.config.json"

SOURCES = ("local", "auto", "download")
DEFAULT_CONFIG = {"source": "local", "url": "", "timeout_seconds": 60}
_SHA = re.compile(r"^[0-9a-f]{64}$")
_BAD_SEGMENT = re.compile(r"^(\.|\.\.|)$")

# The eight languages of the application, so the CLI speaks the chosen one.
MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "local": "Mesh package: source is local, the meshes of the working tree are used; nothing is downloaded.",
        "complete": "All {count} meshes are present and their hashes match.",
        "needed": "{count} meshes are missing or changed.",
        "downloading": "Downloading the mesh package ({size} MiB) from {url}",
        "package_ok": "Package checksum verified.",
        "package_bad": "The package does not match the pinned manifest ({reason}); nothing was installed.",
        "installed": "Installed {count} meshes.",
        "differ": "{count} meshes differ from the manifest: {names}",
        "no_url": "No package address is set (key url in mesh_pack.config.json or HYDRA_UMC_MESH_URL).",
        "bad_source": "Unknown source {value}; use local, auto or download.",
        "failed": "Download failed: {error}",
        "insecure": "Only https addresses are accepted (http only for 127.0.0.1 and localhost).",
    },
    "es": {
        "local": "Paquete de mallas: el origen es local, se usan las mallas del árbol de trabajo; no se descarga nada.",
        "complete": "Las {count} mallas están y sus hashes coinciden.",
        "needed": "Faltan o han cambiado {count} mallas.",
        "downloading": "Descargando el paquete de mallas ({size} MiB) de {url}",
        "package_ok": "Suma de verificación del paquete correcta.",
        "package_bad": "El paquete no coincide con el manifiesto fijado ({reason}); no se instaló nada.",
        "installed": "Instaladas {count} mallas.",
        "differ": "{count} mallas difieren del manifiesto: {names}",
        "no_url": "No hay dirección del paquete (clave url en mesh_pack.config.json o HYDRA_UMC_MESH_URL).",
        "bad_source": "Origen desconocido {value}; usa local, auto o download.",
        "failed": "Falló la descarga: {error}",
        "insecure": "Solo se aceptan direcciones https (http solo para 127.0.0.1 y localhost).",
    },
    "de": {
        "local": "Netzpaket: Quelle ist lokal, die Netze des Arbeitsverzeichnisses werden verwendet; es wird nichts heruntergeladen.",
        "complete": "Alle {count} Netze sind vorhanden und ihre Hashes stimmen.",
        "needed": "{count} Netze fehlen oder wurden geändert.",
        "downloading": "Das Netzpaket ({size} MiB) wird von {url} heruntergeladen",
        "package_ok": "Prüfsumme des Pakets bestätigt.",
        "package_bad": "Das Paket passt nicht zum festgelegten Manifest ({reason}); es wurde nichts installiert.",
        "installed": "{count} Netze installiert.",
        "differ": "{count} Netze weichen vom Manifest ab: {names}",
        "no_url": "Keine Paketadresse gesetzt (Schlüssel url in mesh_pack.config.json oder HYDRA_UMC_MESH_URL).",
        "bad_source": "Unbekannte Quelle {value}; verwende local, auto oder download.",
        "failed": "Download fehlgeschlagen: {error}",
        "insecure": "Nur https-Adressen werden akzeptiert (http nur für 127.0.0.1 und localhost).",
    },
    "fr": {
        "local": "Paquet de maillages : la source est locale, les maillages de l'arborescence sont utilisés ; rien n'est téléchargé.",
        "complete": "Les {count} maillages sont présents et leurs empreintes correspondent.",
        "needed": "{count} maillages manquent ou ont changé.",
        "downloading": "Téléchargement du paquet de maillages ({size} Mio) depuis {url}",
        "package_ok": "Somme de contrôle du paquet vérifiée.",
        "package_bad": "Le paquet ne correspond pas au manifeste fixé ({reason}) ; rien n'a été installé.",
        "installed": "{count} maillages installés.",
        "differ": "{count} maillages diffèrent du manifeste : {names}",
        "no_url": "Aucune adresse de paquet (clé url dans mesh_pack.config.json ou HYDRA_UMC_MESH_URL).",
        "bad_source": "Source inconnue {value} ; utilisez local, auto ou download.",
        "failed": "Échec du téléchargement : {error}",
        "insecure": "Seules les adresses https sont acceptées (http uniquement pour 127.0.0.1 et localhost).",
    },
    "it": {
        "local": "Pacchetto di mesh: la sorgente è locale, si usano le mesh dell'albero di lavoro; non viene scaricato nulla.",
        "complete": "Tutte le {count} mesh sono presenti e gli hash corrispondono.",
        "needed": "{count} mesh mancano o sono cambiate.",
        "downloading": "Download del pacchetto di mesh ({size} MiB) da {url}",
        "package_ok": "Checksum del pacchetto verificato.",
        "package_bad": "Il pacchetto non corrisponde al manifesto fissato ({reason}); non è stato installato nulla.",
        "installed": "{count} mesh installate.",
        "differ": "{count} mesh differiscono dal manifesto: {names}",
        "no_url": "Nessun indirizzo del pacchetto (chiave url in mesh_pack.config.json o HYDRA_UMC_MESH_URL).",
        "bad_source": "Sorgente sconosciuta {value}; usa local, auto o download.",
        "failed": "Download non riuscito: {error}",
        "insecure": "Sono accettati solo indirizzi https (http solo per 127.0.0.1 e localhost).",
    },
    "ja": {
        "local": "メッシュパッケージ：ソースはローカルです。作業ツリーのメッシュを使用し、ダウンロードは行いません。",
        "complete": "{count} 個のメッシュがすべて存在し、ハッシュが一致しています。",
        "needed": "{count} 個のメッシュが不足または変更されています。",
        "downloading": "メッシュパッケージ（{size} MiB）を {url} からダウンロードしています",
        "package_ok": "パッケージのチェックサムを確認しました。",
        "package_bad": "パッケージが固定されたマニフェストと一致しません（{reason}）。何もインストールされていません。",
        "installed": "{count} 個のメッシュをインストールしました。",
        "differ": "{count} 個のメッシュがマニフェストと異なります：{names}",
        "no_url": "パッケージのアドレスが設定されていません（mesh_pack.config.json の url キーまたは HYDRA_UMC_MESH_URL）。",
        "bad_source": "不明なソース {value}。local、auto、download のいずれかを指定してください。",
        "failed": "ダウンロードに失敗しました：{error}",
        "insecure": "https のアドレスのみ使用できます（http は 127.0.0.1 と localhost のみ）。",
    },
    "zh": {
        "local": "网格包：来源为本地，使用工作树中的网格；不会下载任何内容。",
        "complete": "全部 {count} 个网格都存在，且哈希值一致。",
        "needed": "有 {count} 个网格缺失或已更改。",
        "downloading": "正在从 {url} 下载网格包（{size} MiB）",
        "package_ok": "已验证包的校验和。",
        "package_bad": "该包与固定的清单不一致（{reason}）；未安装任何内容。",
        "installed": "已安装 {count} 个网格。",
        "differ": "有 {count} 个网格与清单不一致：{names}",
        "no_url": "未设置包的地址（mesh_pack.config.json 中的 url 键或 HYDRA_UMC_MESH_URL）。",
        "bad_source": "未知来源 {value}；请使用 local、auto 或 download。",
        "failed": "下载失败：{error}",
        "insecure": "只接受 https 地址（仅 127.0.0.1 和 localhost 可用 http）。",
    },
    "pt": {
        "local": "Pacote de malhas: a origem é local, usam-se as malhas da árvore de trabalho; não se transfere nada.",
        "complete": "As {count} malhas estão presentes e os hashes coincidem.",
        "needed": "Faltam ou foram alteradas {count} malhas.",
        "downloading": "A transferir o pacote de malhas ({size} MiB) de {url}",
        "package_ok": "Soma de verificação do pacote confirmada.",
        "package_bad": "O pacote não coincide com o manifesto fixado ({reason}); não foi instalado nada.",
        "installed": "{count} malhas instaladas.",
        "differ": "{count} malhas diferem do manifesto: {names}",
        "no_url": "Não há endereço do pacote (chave url em mesh_pack.config.json ou HYDRA_UMC_MESH_URL).",
        "bad_source": "Origem desconhecida {value}; use local, auto ou download.",
        "failed": "A transferência falhou: {error}",
        "insecure": "Só são aceites endereços https (http apenas para 127.0.0.1 e localhost).",
    },
}


class MeshPackError(Exception):
    """A refusal with a message key; nothing was installed."""

    def __init__(self, key: str, **fields: object) -> None:
        super().__init__(key)
        self.key = key
        self.fields = fields


def language_code(env: dict[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    raw = (env.get("HYDRA_UMC_LANG") or env.get("LC_ALL") or env.get("LANG") or "en").lower()
    code = raw.replace("-", "_").split("_")[0].split(".")[0]
    return code if code in MESSAGES else "en"


def say(key: str, lang: str | None = None, **fields: object) -> str:
    table = MESSAGES.get(lang or language_code(), MESSAGES["en"])
    return table.get(key, MESSAGES["en"][key]).format(**fields)


@dataclass
class Settings:
    source: str = "local"
    url: str = ""
    timeout: float = 60.0


def load_settings(config_path: Path = CONFIG_PATH, env: dict[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    data = dict(DEFAULT_CONFIG)
    if config_path.is_file():
        try:
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update(loaded)
        except (OSError, ValueError):
            pass  # a damaged file falls back to the conservative default
    source = str(env.get("HYDRA_UMC_MESH_SOURCE") or data.get("source") or "local").strip().lower()
    url = str(env.get("HYDRA_UMC_MESH_URL") or data.get("url") or "").strip()
    try:
        timeout = float(data.get("timeout_seconds", 60))
    except (TypeError, ValueError):
        timeout = 60.0
    return Settings(source=source, url=url, timeout=timeout)


def load_manifest(path: Path = MANIFEST_PATH) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    pack = manifest["pack"]
    if not _SHA.match(str(pack.get("sha256", ""))) or not isinstance(pack.get("size"), int):
        raise MeshPackError("package_bad", reason="manifest")
    for entry in manifest["files"]:
        _safe_relative(entry["path"])
        if not _SHA.match(entry["sha256"]):
            raise MeshPackError("package_bad", reason="manifest")
    return manifest


def _safe_relative(rel: str) -> Path:
    parts = rel.split("/")
    if any(_BAD_SEGMENT.match(p) or "\\" in p or ":" in p for p in parts):
        raise MeshPackError("package_bad", reason="path")
    return Path(*parts)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(manifest: dict, mesh_dir: Path = MESH_DIR, deep: bool = False) -> list[dict]:
    """Entries whose file is missing or wrong. Quick mode compares sizes; deep compares SHA-256."""
    bad = []
    for entry in manifest["files"]:
        target = mesh_dir / _safe_relative(entry["path"])
        if not target.is_file() or target.stat().st_size != entry["size"]:
            bad.append(entry)
        elif deep and _sha256_file(target) != entry["sha256"]:
            bad.append(entry)
    return bad


def _check_url(url: str) -> None:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme == "https":
        return
    if parts.scheme == "http" and parts.hostname in ("127.0.0.1", "localhost"):
        return
    raise MeshPackError("insecure")


def download_package(url: str, pack: dict, dest: Path, timeout: float,
                     progress: Callable[[int, int], None] | None = None) -> None:
    """Stream the package to dest, refusing more bytes than the manifest declares, then check its SHA-256."""
    _check_url(url)
    expected = pack["size"]
    h = hashlib.sha256()
    got = 0
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response, dest.open("wb") as out:  # noqa: S310
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                got += len(chunk)
                if got > expected:
                    raise MeshPackError("package_bad", reason="size")
                h.update(chunk)
                out.write(chunk)
                if progress:
                    progress(got, expected)
    except MeshPackError:
        raise
    except OSError as exc:
        raise MeshPackError("failed", error=str(exc)) from exc
    if got != expected:
        raise MeshPackError("package_bad", reason="size")
    if h.hexdigest() != pack["sha256"]:
        raise MeshPackError("package_bad", reason="sha256")


def install_from_package(package: Path, manifest: dict, entries: list[dict], mesh_dir: Path = MESH_DIR) -> int:
    """Write the wanted entries from a package already verified as a whole.

    Two phases so a refusal installs nothing: every wanted blob is first read into a staging folder and hashed
    again, and only when the whole package passed are the files written (each through a .part file and a rename).
    """
    wanted: dict[str, list[dict]] = {}
    for entry in entries:
        wanted.setdefault(entry["sha256"], []).append(entry)
    mesh_root = mesh_dir.resolve()
    targets: list[tuple[str, Path]] = []
    for digest, group in wanted.items():
        for entry in group:
            target = (mesh_dir / _safe_relative(entry["path"])).resolve()
            if mesh_root not in target.parents:
                raise MeshPackError("package_bad", reason="path")
            targets.append((digest, target))
    with tempfile.TemporaryDirectory(prefix="hydra-stage-", dir=package.parent) as stage_name:
        stage = Path(stage_name)
        staged: set[str] = set()
        with tarfile.open(package, mode="r:gz") as tar:
            for member in tar:
                name = member.name
                if not member.isreg() or not name.startswith("blobs/"):
                    raise MeshPackError("package_bad", reason="entry")
                digest = name[len("blobs/"):]
                if not _SHA.match(digest):
                    raise MeshPackError("package_bad", reason="entry")
                if digest not in wanted:
                    continue
                fh = tar.extractfile(member)
                data = fh.read() if fh else b""
                if hashlib.sha256(data).hexdigest() != digest:
                    raise MeshPackError("package_bad", reason="blob")
                (stage / digest).write_bytes(data)
                staged.add(digest)
        if staged != set(wanted):
            raise MeshPackError("package_bad", reason="incomplete")
        for digest, target in targets:
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_name(target.name + ".part")
            tmp.write_bytes((stage / digest).read_bytes())
            os.replace(tmp, target)
    return len(targets)


def ensure(settings: Settings | None = None, manifest_path: Path = MANIFEST_PATH,
           mesh_dir: Path = MESH_DIR, log: Callable[[str], None] = print,
           lang: str | None = None, source: str | None = None) -> int:
    """Bring the meshes to the state the source asks for. Returns the number of meshes written."""
    settings = settings or load_settings()
    mode = (source or settings.source).lower()
    if mode not in SOURCES:
        raise MeshPackError("bad_source", value=mode)
    if mode == "local":
        log(say("local", lang))
        return 0
    manifest = load_manifest(manifest_path)
    bad = scan(manifest, mesh_dir, deep=(mode == "download"))
    if not bad:
        log(say("complete", lang, count=len(manifest["files"])))
        return 0
    log(say("needed", lang, count=len(bad)))
    url = settings.url or manifest["pack"].get("url", "")
    if not url:
        raise MeshPackError("no_url")
    pack = manifest["pack"]
    log(say("downloading", lang, size=f"{pack['size'] / 2**20:.1f}", url=url))
    with tempfile.TemporaryDirectory(prefix="hydra-meshes-") as tmp:
        package = Path(tmp) / pack.get("file", "package.tgz")
        download_package(url, pack, package, settings.timeout)
        log(say("package_ok", lang))
        count = install_from_package(package, manifest, bad, mesh_dir)
    log(say("installed", lang, count=count))
    return count


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # the messages cover ja and zh
        except (AttributeError, ValueError):
            pass
    args = list(sys.argv[1:] if argv is None else argv)
    command = args.pop(0) if args and not args[0].startswith("-") else "status"
    source = None
    if "--source" in args:
        source = args[args.index("--source") + 1]
    lang = language_code()
    try:
        if command in ("status", "check"):
            settings = load_settings()
            manifest = load_manifest()
            bad = scan(manifest, MESH_DIR, deep=(command == "check"))
            if settings.source == "local" and command == "status":
                print(say("local", lang))
            if bad:
                names = ", ".join(e["path"] for e in bad[:5]) + (" ..." if len(bad) > 5 else "")
                print(say("differ", lang, count=len(bad), names=names))
                return 1
            print(say("complete", lang, count=len(manifest["files"])))
            return 0
        if command == "ensure":
            ensure(source=source)
            return 0
        if command == "prepare":  # silent under the default source, so the run scripts can call it every time
            if load_settings().source != "local":
                ensure()
            return 0
        print("usage: python -m hydra_suite.mesh_pack status | check | prepare | ensure [--source auto|download]")
        return 2
    except MeshPackError as exc:
        print(say(exc.key, lang, **exc.fields), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
