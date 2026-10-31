<!--
=============================================================================
HYDRA-UMC - The mesh package
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0 - see LICENSE
=============================================================================
-->

# The mesh package

The 3D models of the viewer (STL, GLB, AMF, 3MF) are the same files in HYDRA-UMC-STUDIO and in HYDRA-UMC-SUITE. They
are **not stored in the repository tree** (they weigh 221 MiB): they come from **one package** with a pinned checksum,
published as a release asset of HYDRA-UMC-MESHES, and are written into `assets/meshes/` before the program starts or is
built. The `ATTRIBUTION.txt`, `metadata.json`, `manifest.json` and colour files of every model folder stay in the tree.

The first run downloads the package (45 MB, one time). **An internet connection is needed once**; after that the package
is kept in a cache folder and reused.

## Choosing the source

`mesh_pack.config.json` (next to `main.py`):

| Key | Default | Meaning |
| --- | --- | --- |
| `source` | `auto` | `auto`: use the local meshes when all are present and fetch only the missing ones. `download`: check every mesh by its SHA-256 and replace the wrong ones (what the CI does). `local`: never touch the network; the meshes of the working tree are used as they are. |
| `url` | empty | Address of the package. Empty means the address in `meshes.pack.json`. Only `https` is accepted (`http` only for `127.0.0.1` and `localhost`, which is what the tests use). |
| `timeout_seconds` | `60` | Network timeout. |
| `cache_dir` | empty | Folder that keeps the downloaded package. Empty means `~/.cache/hydra-umc/meshes`, outside the repository. |
| `package` | empty | An already downloaded package file (see "Working without a network"). |

The environment overrides the file: `HYDRA_UMC_MESH_SOURCE`, `HYDRA_UMC_MESH_URL`, `HYDRA_UMC_MESH_CACHE` and
`HYDRA_UMC_MESH_PACKAGE`. A damaged config file falls back to the defaults.

## Commands

```
python -m hydra_suite.mesh_pack status            # does the tree match the manifest (sizes)?
python -m hydra_suite.mesh_pack check             # the same, comparing the SHA-256 of every file
python -m hydra_suite.mesh_pack ensure            # bring the meshes to the state the source asks for
python -m hydra_suite.mesh_pack ensure --source download
python -m hydra_suite.mesh_pack prepare           # quiet when nothing is missing; what main.py, run.sh and run.bat call
```

`python main.py`, `run.sh` and `run.bat` call `prepare` before starting the program, and `build_exe.bat`, `build_exe.sh`
and `HYDRA-UMC_SUITE.spec` call `ensure` before PyInstaller packs `assets/` (so the installers, which build through
`build_exe`, always carry the models). The offline verifiers (`tools/run_offline_verifiers.py`,
`tests/test_offline_verifiers.py`) call `prepare` first. The messages follow `HYDRA_UMC_LANG` or `LANG` in the eight
languages of the application.

## What a fresh clone, a zip and an update do

- **A clone or a zip of the repository has no meshes.** The first `python main.py`, `run.sh`, `run.bat`, build or test
  run downloads the package. If there is no network and no cached package, the command stops with a message that says
  what to do (below) instead of starting a viewer with no models.
- **An update** (`git pull`, the updater, a new zip) keeps the cache; the package is downloaded again only when a new
  revision is pinned in `meshes.pack.json`.
- **The built program** (`dist/HYDRA-UMC_SUITE`, the `.exe`, the installers) carries the models inside; it downloads
  nothing at run time.

## Working without a network

1. On any computer with Internet, download the file named in `meshes.pack.json` (`pack.file`, from the address in
   `pack.url`). Check it with `sha256sum` (or `Get-FileHash -Algorithm SHA256`): it must equal `pack.sha256`.
2. Copy it to `~/.cache/hydra-umc/meshes/` (on Windows `%USERPROFILE%\.cache\hydra-umc\meshes\`) keeping its name,
   **or** give its path: `HYDRA_UMC_MESH_PACKAGE=/path/to/hydra-umc-meshes-1.tgz python main.py`.
3. Run the command again. The file is verified against the pinned size and SHA-256 before anything is written; a file
   that does not match is refused and nothing is installed.

## What is checked

`meshes.pack.json` is committed in this repository and pins:

- the size and SHA-256 of the package, checked while it is downloaded (an answer larger than the pinned size is cut off)
  and again when a cached or given file is reused;
- the path, size and SHA-256 of every mesh, checked again after extraction.

The package is a `.tgz` that keeps each distinct content once (`blobs/<sha256>`), so a model that is the same in four
machine folders is stored once. Nothing is written until the whole package has passed; every path is checked to stay
inside the mesh folder; files are written through a `.part` file and renamed. A package that does not match installs
nothing and says why. The downloaded file is kept in the cache through a `.part` file too, so an interrupted download
never leaves a half file that looks complete.

`assets/meshes/**` model files are ignored by git, so a download is never committed by mistake; a new model is added
with `git add -f` and goes into a new revision of the package.

## Limits

- The first start, build or test needs the network once, or a package copied by hand (above).
- The cache and the package are verified by size and SHA-256 but not signed: the trust is in the pinned hash committed
  to this repository.

## Tests

`tests/verify_mesh_pack.py` serves a small package from a local server and checks: the manifest tells the truth about
the tree; `local` never touches the network or the disk; `auto` fetches only what is missing; `download` repairs a
changed file; the package is kept in the cache and reused with no network, and a damaged cached package is fetched
again; a package given by path installs with no network and a wrong or missing one is refused; with no network and no
cache the failure carries the file, the address and the cache folder for the hint; a package with another hash, a blob
that does not match its name, an entry outside `blobs/`, a missing blob, an oversized answer, a path with `..` and a
non-`https` address are all refused without installing anything; the messages exist in the eight languages with the same
placeholders.
