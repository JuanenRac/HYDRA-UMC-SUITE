# Changelog

All notable changes to HYDRA-UMC SUITE are summarized here. This file is a
condensed, public-facing summary of the full internal work log kept at
`SONNET/HYDRA-UMC-SUITE/auditoria_historial.txt` (private, not published) -
see that file for exhaustive detail (exact line numbers, verification
transcripts, root-cause analysis).

Versioning: starting with this entry, `hydra_suite/__version__` follows an
odometer-style `MAJOR.MINOR.PATCH` scheme with a base-10 carry rule - patch
goes up by 1 on every real build; once it would pass 9 it resets to 0 and
minor goes up by 1 instead (e.g. `0.1.9` -> `0.2.0`). The version is bumped
automatically by `bump_version.py`, invoked by `build_exe.bat`/`build_exe.sh`
before every PyInstaller build - not on a plain `python main.py` run. See
"Unreleased" below for the change that introduced this.

## [0.1.2]

Builds `0.1.1` and `0.1.2` were bumped automatically by `bump_version.py`
on routine packaged builds; no additional behavior change is on record for
either beyond what's already listed under [0.1.0] below.

## Unreleased

- Added `bump_version.py` and wired it into `build_exe.bat` (step 3/6) and
  `build_exe.sh` (step 4/7), so `hydra_suite/__version__` is bumped
  automatically before every real packaged build, following the base-10
  odometer/carry rule described above.
- The Help > About dialog (`hydra_suite/ui/main_window.py`'s
  `_show_about()`) now shows the real running `__version__` instead of a
  static, version-less message, in all 5 languages.
- Added this CHANGELOG.md; README.md (and its 4 translations) now mention
  the versioning scheme.
- `build_exe.bat`/`build_exe.sh` now print a real startup banner (project
  name, what the script does, author/copyright/license) and no longer
  close their window on their own - a `pause` (Windows) / an `EXIT` trap
  reading input (Linux) keeps the window open on both success and failure
  so the full output, including any error, stays readable.

## [0.1.0]

Everything below happened while the version was still fixed at the initial
`0.1.0` - no numbered releases existed yet, so it is grouped by topic
rather than by version:

**Initial build**
- Full application built from scratch: network discovery (concurrent subnet
  scan against a real HYDRA-UMC STUDIO server's `GET /api/hydra-info`),
  swarm connections (REST + WebSocket per server via `net/client.py`),
  overview/robot-control/3D-viewport/trajectory panels, Photoshop-style
  dockable workspace (native `QDockWidget`), fullscreen startup with F11
  toggle.
- Forward kinematics ported from HYDRA-UMC STUDIO's TypeScript
  (`kinematics.py`), numerically verified bit-for-bit against the
  TypeScript implementation. Real OpenGL 3.3 core-profile viewport with
  real STL meshes (`render/viewport.py`, `render/mesh.py`).
- A new remote API (`GET /api/hydra-info` + WebSocket `/ws`) was designed
  and added directly to the HYDRA-UMC STUDIO server to support this app -
  see that project's own changelog/audit log for the server-side half.

**All 24 robot models + Generic fallback**
- Progressively ported and numerically verified (0.000000mm error against
  the TypeScript reference) all 24 real robot models across the "ur" and
  "quat" kinematic families, plus a primitive-built "Generic" rig. Real
  bugs found and fixed along the way: a GL-context bug in on-demand mesh
  loading (`makeCurrent()`/`doneCurrent()` missing around VAO/VBO
  creation), and the PyInstaller `.exe` bloating to ~280MB from
  `--collect-all PySide6` (fixed by staging only the 4 actually-used Qt
  plugin subfolders, down to ~89-102MB).

**5-language i18n, Cameras panel**
- `hydra_suite/i18n.py` + `language/*.lng` (English/Spanish/Italian/
  French/German), same KEY=Value convention as URTC-FLASHER/URTC-TESTER.
  Cameras panel added (real per-controller camera metadata sync; video
  feed itself an honestly-labeled placeholder, matching STUDIO's own
  `CamerasView.tsx`).

**Reconnaissance audit + live-verified fixes**
- Audit found SUITE had fallen behind the server's now-mandatory JWT auth
  (WebSocket/REST writes were silently broken against a real server) and
  wasn't handling `"delta"` WebSocket messages. Both fixed and verified
  live against the owner's real server, along with an independently
  discovered `websockets` 1 MiB default message-size limit that was
  closing the connection on the first full-state payload (fixed with
  `max_size=None`). `GET /api/system/metrics` wired into the Overview
  panel. `X-Hydra-Client` header added for server-side per-app access
  control; default credentials moved to `admin`/`admin`.

**Three real bugs found against a real server + full doc sweep**
- Root-caused and fixed: (1) network scan silently rejecting a
  user-renamed server (was matching on a customizable display-name field
  instead of payload shape), (2) other-than-active connections in the
  swarm frozen at "Connecting..." forever regardless of real login
  outcome, (3) the 3D viewport repainting on *every* WebSocket tick for
  *any* robot in the swarm instead of only its own robot (fixed by
  comparing joint state before triggering a repaint). README.md and
  `docs/ROADMAP.md` rewritten to explain current design decisions rather
  than narrate a change history.

**5-language README translations**
- `README_spa.md`/`README_ita.md`/`README_fra.md`/`README_deu.md` added as
  full, faithful translations of the English README, matching the
  URTC-FLASHER/URTC-TESTER documentation pattern; CC BY-SA 4.0 license
  note added for the documentation itself (separate from the GPL-3.0 code
  license).

**Full line-by-line review of all 30 .py files**
- Two further real bugs found and fixed: trajectory points silently wiped
  on every unrelated swarm state tick (data loss), and failed writes
  (`push_state()`) being swallowed silently with no error surfaced to the
  UI, plus a related bug where a failed write was incorrectly marked as
  "delivered" and could never be retried.

**mejoras_futuras.txt sweep + real mDNS**
- Fixed a duplicate-host scan when two local IPv4 addresses share a /24,
  and an Overview panel that rebuilt its entire table on every unrelated
  state tick. Real mDNS discovery implemented with `zeroconf`
  (`discover_mdns()`, merged concurrently with the existing subnet scan
  in `discover_servers()`), verified end-to-end against a real published
  `_hydra._tcp` service.

## License

This file is documentation and, like README.md and its translations, is
available under CC BY-SA 4.0 (see README.md's "License and Copyright
Notices" section).
