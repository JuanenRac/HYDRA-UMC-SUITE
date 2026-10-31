<!--
=============================================================================
HYDRA-UMC - The mesh package
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0 - see LICENSE
=============================================================================
-->

# The mesh package

The 3D models of the viewer (STL, GLB, AMF, 3MF) are the same files in HYDRA-UMC-STUDIO and in HYDRA-UMC-SUITE.
Besides the copy in the working tree (`assets/meshes/`), they can come from **one package** with a pinned checksum, so
a build or an installer does not have to carry them.

The default is unchanged: **the meshes of the working tree are used and nothing is downloaded.**

## Choosing the source

`mesh_pack.config.json` (next to `main.py`):

| Key | Default | Meaning |
| --- | --- | --- |
| `source` | `local` | `local`: never touch the network. `auto`: use the local meshes when all are present and fetch only the missing ones. `download`: check every mesh by its SHA-256 and replace the wrong ones. |
| `url` | empty | Address of the package. Empty means the address in `meshes.pack.json`. Only `https` is accepted (`http` only for `127.0.0.1` and `localhost`, which is what the tests use). |
| `timeout_seconds` | `60` | Network timeout. |

The environment overrides the file: `HYDRA_UMC_MESH_SOURCE` and `HYDRA_UMC_MESH_URL`. A damaged config file falls back to
`local`.

## Commands

```
python -m hydra_suite.mesh_pack status            # does the tree match the manifest (sizes)?
python -m hydra_suite.mesh_pack check             # the same, comparing the SHA-256 of every file
python -m hydra_suite.mesh_pack ensure            # bring the meshes to the state the source asks for
python -m hydra_suite.mesh_pack ensure --source auto
python -m hydra_suite.mesh_pack prepare           # silent under `local`; what run.sh and run.bat call
```

`run.sh` and `run.bat` call `prepare` before starting the program, so with `source` set to `auto` a clone without the
mesh files fetches them on the first run. The messages follow `HYDRA_UMC_LANG` or `LANG` in the eight languages of the
application.

## What is checked

`meshes.pack.json` is committed in this repository and pins:

- the size and SHA-256 of the package, checked while it is downloaded (an answer larger than the pinned size is cut off);
- the path, size and SHA-256 of every mesh, checked again after extraction.

The package is a `.tgz` that keeps each distinct content once (`blobs/<sha256>`), so a model that is the same in four
machine folders is stored once. Nothing is written until the whole package has passed; every path is checked to stay
inside the mesh folder; files are written through a `.part` file and renamed. A package that does not match installs
nothing and says why.

## Tests

`tests/verify_mesh_pack.py` serves a small package from a local server and checks: the manifest tells the truth about
the tree; `local` never touches the network or the disk; `auto` fetches only what is missing; `download` repairs a
changed file; a package with another hash, a blob that does not match its name, an entry outside `blobs/`, a missing
blob, an oversized answer, a path with `..` and a non-`https` address are all refused without installing anything;
the messages exist in the eight languages with the same placeholders.
