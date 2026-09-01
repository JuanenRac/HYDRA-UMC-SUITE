# Changelog

All notable changes to HYDRA-UMC SUITE are summarized here. This file is a
condensed, public-facing summary of the full internal work log, which is
kept private and not published - exhaustive detail (exact line numbers,
verification transcripts, root-cause analysis) lives only in that private
log.

Versioning: starting with this entry, `hydra_suite/__version__` follows an
odometer-style `MAJOR.MINOR.PATCH` scheme with a base-10 carry rule - patch
goes up by 1 on every real build; once it would pass 9 it resets to 0 and
minor goes up by 1 instead (e.g. `0.1.9` -> `0.2.0`). The version is bumped
automatically by `bump_version.py`, invoked by `build_exe.bat`/`build_exe.sh`
before every PyInstaller build - not on a plain `python main.py` run. See
"Unreleased" below for the change that introduced this.

## [Unreleased]

- **Visual command deck**: added a persistent top-level command surface that
  raises Suite's real Overview, Robot Control, Cameras, Trajectory and Logs
  docks. It reports the actual active connection state, selected target and
  UTC clock rather than showing hard-coded operational data.
- **Unified ecosystem visual language**: refreshed the industrial Qt style
  with the deep-navy, cyan and readable technical-control palette established
  by HYDRA-UMC-UPDATER. Added the official HYDRA-UMC SVG/ICO mark for the
  window, taskbar and command deck. The command deck renders the SVG through
  `QSvgWidget`/`QSvgRenderer`, so its supported six-second transform animation
  plays in-window; the taskbar/window ICO remains intentionally static. The
  source SVG and reproducible ICO remain first-class project assets. The QSS
  now uses the same 16px section shells, 11px metric cards and 10px interactive
  controls as the Updater command deck.
- Added the command-deck labels to all seven Suite language files and
  synchronized the public README languages with the real visual behavior.

## [0.1.9]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.1.8] - Joint jog now atomic + debounced; speed/acceleration now debounced

- **`hydra_suite/ui/panels/robot_control.py`** - the joint knob/slider
  (`JointRow`) now fires the real atomic `jog` command instead of
  mutating state and calling `push_active_state()`'s own full-tree
  read-modify-write - the same real gap class (DISEÑO_SYNC_DELTAS.txt
  CAUSA A) already fixed for this panel's own speed/acceleration
  sliders, just never fixed for the joint knob itself until now. Sends
  the real `joints` override contract `server.ts`'s own `"jog"` case
  accepts (`axis:'x'`/`amount:0`/`target:'robot'` + an explicit 6-joint
  override) - the same mechanism `HYDRA-UMC-STUDIO`'s `handleJ1Jog()`/
  `HYDRA-UMC-ANDROID-CONTROL`'s `jogJ1()` already use for a single-joint
  absolute set.
- **`hydra_suite/net/client.py`** - `HydraConnection.send_command()`
  gained a real `debounce_ms` parameter: the optimistic `local_mutate`
  still applies instantly on every call (so a dragged
  `RotaryKnob`/`QSlider` still gets per-tick visual feedback), but the
  real network POST is now coalesced - any still-pending send for the
  same command name is cancelled before scheduling a new one, so a fast
  drag collapses into a handful of real requests instead of one per
  mouse-move tick. Same real mechanism `HYDRA-UMC-ANDROID-CONTROL`'s own
  `sendAtomicCommand(debounceMs=...)` already uses, and
  `HYDRA-UMC-IOS-CONTROL`/`HYDRA-UMC-DSI`'s own
  `RobotViewModel._sendAtomicCommand(debounce:...)` now use too (fixed
  this same session). The joint knob uses a 50ms debounce; the speed/
  acceleration sliders (previously undebounced despite already using the
  atomic path) now use 300ms, matching Android's own `setSpeed()`.
- **Added `tests/verify_send_command_debounce.py`** (new) - exercises
  the real `HydraConnection.send_command()` debounce state machine
  directly (only `httpx.AsyncClient.post` is monkeypatched, not the
  debounce logic itself): a rapid burst for the same command collapses
  into exactly one real POST carrying the last value; two different
  command names never coalesce into each other; `debounce_ms=0` still
  sends immediately with zero behavior change for every existing caller.

## [0.1.7] - Real, deterministic coverage for net/discovery.py's pure logic

- **Added `tests/verify_discovery.py`** (new) - net/discovery.py's
  subnet-scan and real mDNS discovery (`_hydra._tcp`, matching the
  service `server.ts`/`HYDRA-UMC-IOS-CONTROL` already use) were already
  real and complete, but had zero automated coverage: `test_net_manual.py`
  only exercises `probe_host()` against an already-running real server,
  by hand, and can't run in CI. This new script needs no network, no
  real server, and no zeroconf multicast socket - it verifies
  `candidate_hosts_for()`'s pure `/24` enumeration directly, and
  `discover_servers()`'s own `(host, port)` dedup logic across its two
  concurrent sources by monkeypatching `scan_subnets`/`discover_mdns` to
  fake async generators (confirming an entry both fake sources yield is
  reported exactly once). Same real/no-hardware-needed verification
  boundary this ecosystem already applies everywhere else, following
  this repo's own existing `verify_*.py` convention (a plain script with
  a `failures` counter and `sys.exit(1)`, not a pytest suite - this repo
  has none).

## [Unreleased] - Chinese and Japanese added to the language menu

- New `language/chinese.lng` (简体中文) and `language/japanese.lng` (日本語) -
  full translation of all 85 keys, matching the coverage of the existing
  english/spanish/italian/french/german files. Added to `i18n.py`'s own
  `AVAILABLE_LANGUAGES` list, which the Language menu builds from
  dynamically - no other UI code needed changing. Verified two ways: a
  real `load_language()` call for both new files confirmed all 85 keys
  present with zero gaps against `english.lng`, and a real offscreen Qt
  `MainWindow()` instantiation confirmed both new entries render correctly
  in the actual Language menu alongside the other 5.
- New `README_zho.md` / `README_jpn.md` documentation translations, plus
  the 5 existing README files' language selectors updated to link them.
- Doesn't bump `hydra_suite/__version__` on its own - this project's own
  versioning convention only advances it on a real `build_exe.bat`/`.sh`
  packaged build, not on every source change (see the versioning note
  above).

## [Unreleased] - Installer scripts (Windows/Linux)

- New `installer/` - `windows_installer.iss` + `build_installer.bat`
  (Inno Setup, a real Windows installer with Start Menu/uninstall
  entries) and `build_deb.sh` (a real `.deb`, `dpkg-deb`-based). Both
  delegate the actual app build to this project's own existing
  `build_exe.bat`/`.sh`, only adding packaging on top.
- **Not run end-to-end this session** - neither Inno Setup nor
  `dpkg-deb` was available in the environment that wrote them (installing
  new system-wide tooling wasn't done without asking first). What was
  verified: `build_deb.sh` passes a real `bash -n` syntax check, and its
  version-extraction + package-tree-assembly logic was dry-run in
  isolation (a placeholder binary through the real script logic),
  producing the exact expected file tree and a correct `DEBIAN/control`.
  See `installer/README.md`'s own "Verification status" for the honest
  caveat - treat both as written and reasoned through, not yet proven,
  until someone with the right tooling runs one for real.

## [0.1.7]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.1.6] - Ecosystem panels: real charts, card layouts, cross-referenced data (STUDIO 0.2.9 parity)

Direct user feedback after `0.1.5`: the 5 Ecosystem panels were
functionally real but visually and functionally thin - flat tables, no
charts, no way to filter, panels that didn't talk to each other. Same
real data sources throughout, raised to match HYDRA-UMC STUDIO's own
`0.2.9` redesign:

- **`EcosystemTelemetryPanel`** - real charts via `PySide6.QtCharts`
  (already part of the PySide6 dependency this app ships, unused
  anywhere in this app until now): a `QLineSeries` for raw points, a
  `QBarSeries` for aggregated buckets, both dark-themed to match this
  app's own palette. Added a real min/max/avg/count stat row and quick
  time-range preset buttons (5m/1h/6h/24h).
- **`EcosystemServicesPanel`** - grouped by family into a real card grid
  (the same grouping the manifests themselves already carry), with a
  search box, per-family filter buttons, and a total/live/families stat
  row.
- **`AiFamilyStatusPanel`** (new panel, closing a real parity gap - `0.1.5`
  shipped 5 panels, STUDIO's own `0.2.6` shipped 6) - filters the same
  ecosystem-status scan to "Vision AI Node"/"Cognitive AI Node", and
  cross-references `HydraState.ai_hailo` (new property, `models.py`) -
  the SAME server-persisted `settings.aiHailo` field STUDIO's own
  Config > AI/Hailo tab writes, not a SUITE-only concept - so a family
  with real live nodes but its configured Hailo device set to "None"
  surfaces a real, actionable warning banner here too.
- **`AdminClientsPanel`** - admin-first sort, a live "Xm ago" connection
  duration (ticking every second via its own `QTimer`, independent of
  the 5s data poll), role-colored badges, connected/admin-count stats.
- **`AdminLogsPanel`** - a real search box plus tag filter buttons
  extracted client-side from each line's own `[TAG]` prefix (the same
  real convention `AdminLogs.tsx`'s redesign uses).
- **`AdminServerPanel`** - now also shows a real live snapshot from the
  new `HydraConnection.fetch_hydra_info()` (product, uptime,
  controller/robot counts, hostname) above the port-config form.
- i18n: 29 new keys across all 7 `language/*.lng` files.
- Verified for real: a real offscreen Qt session constructing the actual
  `MainWindow` (zero exceptions across all 6 Ecosystem panels), the real
  chart-rendering methods (`_render_line_chart`/`_render_bar_chart`) and
  the card-rebuild methods exercised directly with real sample data (not
  just construction), a real HTTP round-trip proving
  `fetch_hydra_info()` parses a real response, and `HydraState.ai_hailo`
  checked against both a populated and an empty settings tree.

## [0.1.5] - HYDRA-UMC menu becomes a real ecosystem control/visibility surface (STUDIO parity)

- 5 new dockable panels, desktop counterparts to the same-named panels
  added to HYDRA-UMC STUDIO's own web UI this same session:
  `EcosystemServicesPanel` (`GET /api/ecosystem/status` - real manifest
  scan + live TCP/HTTP probe of every sibling HYDRA-UMC-* checkout that
  declares a port; view + manual refresh only, no start/stop - no
  process supervisor exists anywhere in the ecosystem today),
  `EcosystemTelemetryPanel` (raw points or bucketed aggregates against
  HYDRA-UMC-DATALAKE through Server's new `/api/telemetry/*` proxy), and
  3 admin-only panels - `AdminClientsPanel`, `AdminLogsPanel`,
  `AdminServerPanel` - against Server's existing `/api/admin/*` routes,
  the same ones its own `admin-ui/` reference app and STUDIO's new
  `AdminClients.tsx`/`AdminLogs.tsx`/`AdminServer.tsx` already use.
- **`net/client.py`** - `HydraConnection` gained a shared `_request_json()`
  helper and 8 new methods on top of it (`fetch_ecosystem_status`,
  `fetch_telemetry_query`/`fetch_telemetry_aggregate`,
  `fetch_admin_clients`/`fetch_admin_logs`/`fetch_admin_server_config`/
  `save_admin_server_port`/`restart_server`). `login()` now also captures
  `role` from `/api/login`'s own response (`is_admin` property) - same
  field STUDIO's `store.tsx` now reads too - so the 3 admin-only panels
  above only show real data for a genuinely admin session, matching
  Server's own `requireAdmin` gate on those routes rather than just
  surfacing whatever 403 comes back.
- i18n: 70 new keys across all 7 `language/*.lng` files (was 85 keys,
  now 155), every key cross-checked 1:1 against actual `_()` call sites
  in the 5 new panels.
- Verified for real, not just compiled: a real offscreen Qt session
  (`QT_QPA_PLATFORM=offscreen`) constructing the actual `MainWindow` -
  all 5 new panels build with zero exceptions alongside every existing
  one - plus a real HTTP round-trip against a throwaway `http.server`
  stub proving `HydraConnection`'s 2 new fetch methods parse a real
  200 and a real 403 response correctly. `python -m py_compile` on every
  changed file, and every `language/*.lng` file re-parsed to confirm
  identical key sets across all 7 languages.

## [0.1.4] - Removed the hardcoded admin/admin login default

- **`models.py`/`server_browser.py`** - `ServerInfo` and the manual/edit
  connection dialogs no longer pre-fill `admin`/`admin`. Production
  HYDRA-UMC-SERVER instances refuse to seed that source-known account
  now (see that repo's own fail-closed bootstrap changelog entry), so a
  discovered server is never treated as an implicit authorization grant.
  Both dialogs now refuse to add or update a connection with an empty
  username or password.
- `SECURITY.md` documents the real expectation.
- `tools/ci_validate.py` gained `validate_local_markdown_links()`,
  rejecting a relative Markdown link whose target file doesn't exist.
- `CI_VALIDATION=PASS`, `PYTHON_COMPILE=PASS`.

## [0.1.3] - Real-time log viewer with filters

- New `logging_handler.py` bridges Python's own stdlib `logging` (every
  module already does `logging.getLogger(__name__)`) into a Qt signal -
  root logger level raised from the default WARNING to INFO so the
  `.info()` calls already scattered through this codebase actually
  reach it, without also pulling in PySide6/asyncio's own DEBUG-level
  internal noise.
- New "Logs" dock (`ui/panels/logs_panel.py`, tabbed with Cameras by
  default) - level dropdown + text search filter the DISPLAY only, the
  full history stays intact underneath so clearing a filter always
  brings everything back, not just what arrived since the filter
  changed.
- Verified with real `logging.getLogger(...).info/warning/error()` calls
  captured live through the real handler into a real `LogsPanel`
  (offscreen Qt, no display needed): all 3 real levels appeared
  correctly, the ERROR filter correctly hid the other two, clearing the
  filter brought them back, the text search correctly isolated one
  entry, and Clear correctly emptied both the display and the
  underlying history. Real `MainWindow()` instantiation also confirmed
  the new dock and its View-menu toggle wire in without errors.

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
