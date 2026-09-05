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

- **Real Qt Quick command-deck shell, the "redesign from zero" this
  project needed** after both real ways of embedding QML inside the
  established `QMainWindow`+`QDockWidget` tree proved unsafe:
  `QQuickWidget` painted solid black; `QQuickView`+`createWindowContainer`
  rendered correctly in isolation but corrupted sibling widgets' real
  Z-order inside this app's actual 26-dock layout (NavSidebar vanished,
  panels visually overlapped - reverted before shipping). New
  `qt_suite.py`/`assets/qml/Main.qml` are a STANDALONE pure-QML
  `ApplicationWindow` instead - the same real shape as
  HYDRA-UMC-OS-REBUILDER/HYDRA-UMC-UPDATER/URTC-TESTER/URTC-FLASHER
  (all of which already render correctly), not an embed, so the mixing
  problem those two failed attempts hit doesn't apply here.
  `hydra_suite.app.SuiteController` is reused completely unchanged - it
  was already a plain, toolkit-agnostic `QObject` with Qt Signals.
  Navigation trades `QDockWidget`'s float/split/tab-merge flexibility
  for HYDRA-UMC-STUDIO's own simpler nav-sidebar-plus-single-content-
  pane shape (the real taxonomy - `ROOT_ITEMS`/`INDUSTRIAL_ITEMS`/
  `URTC_ITEMS`/`HYDRAUMC_ITEMS`/`HYDRAUMC_ECOSYSTEM_ITEMS` - is
  transcribed from `nav_sidebar.py`'s own real source of truth, not a
  third invented one), a deliberate real design choice per the
  STUDIO<->SUITE parity rule. Run `python main.py --qtquick` to see
  this shell - the classic, fully-functional `QDockWidget` app remains
  the default entry point, same opt-in convention URTC-TESTER/
  URTC-FLASHER used while THEY were mid-migration. New
  `verify_qt_suite_shell.py` (real nav-taxonomy parity check against
  `nav_sidebar.py`'s own `ALL_DOCK_KEYS`, real per-panel assertions
  against the real backend objects, zero-QML-warnings load check).

  **Real, honest status** - 11 of the 26 real panels are ported to
  actual QML content so far; every other one shows a real "not yet
  migrated" placeholder (a small amber dot next to its nav label)
  rather than a fake, empty-but-styled panel pretending to be done:
  - **Servers** - the swarm's real entry point: network scan, manual
    add, per-row status/active/credentials/remove.
  - **Overview** - Active Controller/System Metrics cards + robot
    table, from real `SuiteController` signals.
  - **Logs** - this app's own local Python log, real level/text
    filtering.
  - **Robot Control** - real per-joint jog sliders and speed/
    acceleration, routed through the exact same atomic, debounced
    `send_robot_command()`/optimistic-update path the classic panel
    uses. `RotaryKnob`'s own custom dial isn't reproduced - a `Slider`
    alone already sets the identical real value.
  - **Trajectory** - the same real local-only point recorder as the
    classic panel (record/jog-to-point/delete); points reset only when
    the selected robot itself changes.
  - **AI Family Status** - the real `GET /api/ecosystem/status` scan
    filtered to the 2 real AI families, cross-referenced against the
    same server-persisted `settings.aiHailo` field STUDIO's own Config
    tab writes, warning when a family has live projects but no Hailo
    device configured.
  - **Admin Clients** ("Connected Apps") - every live WebSocket
    connection to the active server right now, admin-first sort, a
    live "Xm ago" duration ticking every second independent of the 5s
    data poll, exactly matching the classic panel's own two-timer
    design.
  - **Admin Logs** ("Server Log") - the remote Server's own on-disk
    log, real tag extraction/filtering, and the same real "clear the
    screen, keep tailing" anchor trick as the classic panel.
  - **Admin Server** ("Server Configuration") - listen-port config (a
    save never rebinds the live socket, same real note as the classic
    panel), a live `GET /api/hydra-info` snapshot, and a graceful
    restart behind a new shared confirm dialog every future destructive
    action in this shell can reuse.
  - **Ecosystem Services** - the same real `GET /api/ecosystem/status`
    scan AI Family Status uses, grouped into a real card grid by family
    with the same 5-state health color/badge logic and admin-only
    Start/Stop/Restart per card (Stop/Restart behind the shared confirm
    dialog).
  - **Ecosystem Telemetry** - the same real two modes
    HYDRA-UMC-DATALAKE's own API exposes (raw points via
    `GET /api/telemetry/query`, bucketed via `/aggregate`), quick
    time-range presets, and a min/max/avg/count stat row. Chart
    rendering is a hand-drawn QML `Canvas` (a real polyline for raw
    points, real bars for aggregated buckets) rather than
    `import QtCharts` in QML - that module segfaults on load in this
    real environment (PySide6 6.11.1, confirmed both offscreen and
    on-screen - a real crash, not a test artifact).
  - **XY Table** - the same real, deliberately-preserved
    `hasXYTable`/`xyTable` quirk the classic panel already documents:
    Enable sets only the flag (the settings page shows with a 500mm
    display fallback, but the real config object doesn't exist yet, so
    width/jog are genuine no-ops) until Reset actually creates one
    (writing 300mm - a real, different number from the display
    fallback). Own independent robot selection, not shared with Robot
    Control/Trajectory, matching the classic panel's own separate
    combo box. The right-hand "3D Live View" isn't ported, same real,
    separate omission as every panel in this family.
  - **Rack Manager** - the same real, deliberately-preserved quirk the
    classic panel's own header documents: Reset resets BOTH rack1 and
    rack2 back to their real seed defaults (rack1=Input, rack2=Output)
    regardless of which rack's own Reset button was clicked, discarding
    any local changes to either. A real decimal-capable `SpinBox`
    (QML's own is integer-only by default) for the 2-decimal joint/
    table position fields.
  - **Pick and Place** - the Machine combo (JuanenPnP/LumenPnP), real
    Enable/Remove/Reset, and the 5 pose-preview sliders (X/Y/Z axis,
    both nozzle rotations) bound to the classic panel's own real fixed
    hardware bounds (433mm/487mm/90mm travel, ±180° nozzle) - each
    machine type keeps its own independent module block, exactly like
    the classic panel's real per-`machineType` state. Manual pose
    preview only, same real scope as the classic panel (neither PnP
    machine has a live firmware feed yet). The right-hand "3D Live
    View" isn't ported, same real, separate omission as every panel in
    this family. **Real bug caught by this panel's own on-screen
    screenshot before shipping**: the axis `SpinBox`es' numeric field
    was too narrow (90px) to fit the real fixed-bound values -
    "250"/"-90" rendered as just their last digit while the paired
    `Slider` sat at the correct position the whole time. Widened to
    150px.
  - **Kinematic Brain Stage** - UNLIKE every panel above, this is
    CONTROLLER-level state (one Kinematic Brain per controller), so it
    has no robot selector at all, matching the classic panel's own
    header note. XY gantry jog (X/Y1/Y2/Z, real step presets, real
    per-axis bound clamping) + table size, heated bed (thermistor
    readouts, target temp, SSR toggle), ATC revolver (prev/next, tool
    count, homed indicator, real negative-index-wraparound handling),
    conveyor (install-then-run/speed, hidden until installed, matching
    the classic panel's own real "not installed yet" state), a
    12-button Endstops grid, and 3 checkable toggle-button grids (Fans/
    Pumps/Valves) via one new reusable `ToggleGrid` QML component
    instead of hand-rolling the grid 3 times.
  - **CNC, Laser, Heated Bed and Vacuum Table** - all 4 real nav keys
    share ONE generic bridge implementation and QML `Component`,
    mirroring `module_config_panel.py`'s own `ModuleConfigPanel(module_key,
    heading_key, machine_name)` parameterization exactly (robot
    selector, enable/disable, width/length, reset) instead of 4
    near-duplicate ports - each nav key still keeps its own real,
    independent robot selection. Heated Bed's and Vacuum Table's own
    real "extra" shapes (SSR toggle/target temp/thermistor readouts;
    pump/valve toggles) are gated by a real `moduleExtraKind` property
    rather than 4 separate QML files. Reproduces Vacuum Table's own
    real, if minor, inconsistency faithfully: it DISPLAYS the same
    500mm fallback as the other 3 modules before anything is written,
    but its own Reset writes 100mm - a genuine mismatch already present
    in HYDRA-UMC-STUDIO's own source, not invented here. The right-hand
    "3D Live View" isn't ported for any of the 4, same real, separate
    omission as every panel in this family.
  - **ATC Tools Configuration** - a genuinely fresh, purpose-built port
    (NOT built on the generic Module Config shape above - `RobotView.atc`
    is `None` when unconfigured with no separate `enabled` flag, unlike
    every other tool attachment): all 3 real layout modes (vertical/
    horizontal panel, revolver), the 25-item real URTC tool catalog per
    slot, a real 6-joint (+ table tx/ty when this robot has one) position
    editor per panel slot and for the revolver's own base pickup
    position, real JSON export/import with the same validation the
    classic panel's own `QMessageBox.warning()` does (round-tripped
    end-to-end against a real temp file in `verify_qt_suite_shell.py`,
    not just in-memory state), and the real 2D graphic representation
    (grid of slots, or a circular revolver) as a hand-drawn QML `Canvas`
    - genuinely ported this time, not the family's usual 3D-viewport
    omission, since the classic panel's own graphic is from-scratch
    QPainter/CSS on both sides already, not a 3D dependency. **Real bug
    caught by this panel's own on-screen screenshot before shipping**:
    the position-editor `SpinBox`es repeated the exact same too-narrow
    (90px) mistake Pick and Place already found and fixed - a real value
    of 45 rendered as "5". Widened to 150px; confirmed fixed with a
    second screenshot, in both panel and revolver mode.

## [0.3.9]

- **Real left navigation panel, matching HYDRA-UMC-STUDIO's own structural scheme** - real user feedback: SUITE's flat top-toolbar navigation didn't match STUDIO's own left-panel menu/submenu layout ("no tiene el mismo esquema de estructura que studio... con su panel izquierdo con los menu y submenus"). New `NavSidebar` (`ui/nav_sidebar.py`) ports that same real shape - a root menu plus 3 real drill-down submenus (Industrial/URTC/HYDRA-UMC, each with its own Back-to-Root control) - onto this app's own real dock system: every button shows+raises one of the same real `QDockWidget` panels the old toolbar buttons did, nothing about the underlying dockable/floatable/tabbable panel system changed. The command deck keeps only what a flat toolbar still suits (branding, live connection status, About); its 5 former nav buttons moved into the sidebar. New real test (`tests/verify_nav_sidebar.py`) diffs the sidebar's own dock-key coverage against `main_window.py`'s real `self._docks` 1:1, so a future dock added to one file and forgotten in the other fails a real test.

## [0.3.8]

- **Fixed a real permanent-freeze bug in the Cameras panel's own stream
  loop** - the SUITE-side port of the same live user report that fixed
  it in HYDRA-UMC-STUDIO (camera 4, 2 real streams: after enough
  switches, the feed stopped reconnecting at all). `_run_stream()` used
  to try exactly once - if `iter_mjpeg_frames()` ended after already
  showing real frames (the server's own camera-process supervisor
  killing and respawning a hung capture process, up to ~30s between its
  own attempts - see HYDRA-UMC-SERVER's CHANGELOG), this task just
  silently stopped: no error shown, the last real frame frozen on
  screen forever, no further attempt made unless an unrelated state
  broadcast happened to call `_start_stream()` again later. Now loops on
  its own with a real capped backoff (1.5s up to 15s), resetting to fast
  retries the moment a real frame arrives again - only `task.cancel()`
  (camera off, card removed) ends it.
- **New real PTZ (pan/tilt/zoom) control - IP cameras only**, matching
  HYDRA-UMC-STUDIO's own Vision Center one-to-one. A checkable toggle
  next to the video area reveals a real direction/zoom pad; each button
  sends a real continuous-move command on press and a real stop on
  release, through HYDRA-UMC-SERVER's new `POST /api/camera/:id/ptz`
  (new `HydraConnection.send_ptz()`). A camera with no real PTZ hardware
  shows the server's own honest error instead of pretending the move
  worked. New `BTN_PTZ_TOGGLE`/`MSG_PTZ_FAILED` keys × 7 languages. Real
  headless test coverage extended in `tests/verify_cameras_panel.py`
  (toggle visibility gated on source type, a real send call forwarding
  this camera's own host/credentials, an honest-failure response shown
  and not swallowed, the toggle hiding itself again on a USB switch).
- **Documentation audit: every community-health doc (`CODE_OF_CONDUCT.md`/`CONTRIBUTING.md`/`SECURITY.md`/`SUPPORT.md`/`LICENSE.md`/`installer/README.md`) is now actually linked from the README** (new "📚 Documentation & Community" section, all 7 languages) - a real gap found while checking every doc file's own README-linkage requirement: these 6 files existed and were content-accurate, but nothing in any README pointed to them, in any language. Cross-checked against `HYDRA-UMC-STUDIO`'s own README and found the identical pattern there too - likely an ecosystem-wide gap, not unique to this repo, tracked separately for the rest of the ecosystem.
- **Live 3D preview for the Pick & Place panel (`juanenPnP`/`lumenPnP`), real STL mesh, closing the last gap in this parity effort** - real port of STUDIO's own `LumenPnPRig.tsx`, the one tool-attachment module with a real merged mesh instead of primitive geometry. New `assets/meshes/lumenpnp/` (the 5 real `.stl` files - `base`/`y_carriage`/`x_carriage`/`z_carriage_n1`/`z_carriage_n2` - copied verbatim from `HYDRA-UMC-STUDIO/public/models/lumenpnp/`, tessellated from Opulo's own official FreeCAD source; see that folder's own `ATTRIBUTION.txt` for the full provenance and why, unlike STUDIO's own `.glb`-only loading, this app loads the raw `.stl` directly - the browser-specific WebGL context-lost bug that forced STUDIO onto a pre-merged `.glb` has no equivalent in a desktop PyOpenGL app, so no new mesh format support was needed, just the existing `mesh.py`/`load_link_set()` path every other robot mesh already uses). New `hydra_suite/render/pnp_rig.py`: `pnp_world_link_transforms()`, a real Cartesian-gantry chain (base fixed -> y_carriage translates world Y -> x_carriage translates local X -> z_carriage_n1/n2 translate local Z and each rotate about their own Z for their own nozzle) - not a serial joint chain like `kinematics.py`'s UR/quaternion families, and not the flat WORLD-space `Segment` list `module_rig.py`'s 4 primitive modules use either, since this rig genuinely moves per real axis values. `RobotViewport` gained a parallel `set_attached_pnp()` module-only mode (independent of `set_attached_module()`'s primitive path - the mesh-loading/draw path genuinely differs) with the same lazy-load-on-first-GL-context-availability pattern every robot's own mesh set already uses. `PickAndPlacePanel` now embeds its own `RobotViewport` side by side with the pose-preview sliders, live on enable/disable/machine-switch, and - the same real gap this pass also fixed in the CNC/Laser/Heated Bed/Vacuum Table port below - `_on_axis_changed()` now refreshes the preview immediately instead of waiting for the next state broadcast round-trip. Real headless test coverage added to `tests/verify_pick_and_place_panel.py`: the real gantry chain composition (base stays fixed, y/x carriages compose correctly, both nozzles share the same real position and differ only in rotation), `RobotViewport.set_attached_pnp()`'s pending-mesh-load cache path, and the panel driving its own embedded viewport from real enable/axis-change/machine-switch/disable transitions - plus a real GL-context smoke check (actual `.stl` load, actual GPU buffer build, actual paint pass) confirming the real triangle counts match STUDIO's own `ATTRIBUTION.txt` figures exactly (base 32,640 / y_carriage 23,858 / x_carriage 19,188 / each nozzle 5,474). This closes the tool-attachment live-3D-preview gap completely - all 5 modules that have one on STUDIO's own side now have one here too.
- **Live 3D preview for the CNC/Laser/Heated Bed/Vacuum Table config panels** - real port of STUDIO's own per-panel right-hand "3D Live View" (`SharedModule3DView.tsx`, a react-three-fiber `<Canvas>`), previously deliberately NOT ported because this app's own 3D renderer (`render/viewport.py`'s `RobotViewport`) had no support for rendering an attached tool module's own geometry at all - a real gap, not a shortcut, as that file's own former header comment said explicitly. New `hydra_suite/render/module_rig.py`: the same box/cylinder geometry as `SharedModule3DView.tsx` - same shapes, positions, and hex colors, at the same real mm-to-meter scale - for the 4 module types that have one on STUDIO's own side (`juanenCNC`/`juanenLaser` share `LumenStyleFrame`'s legs/rails/gantry/toolhead; `heatedBed`/`vacuumTable` get their own simpler stacks); any other module key (ATC, XY Table, Rack Manager, Pick & Place, Kinematic Brain Stage, Flasher, Tester) returns an empty segment list - none of those have a live preview on STUDIO's own side either, so a blank viewport there is faithful, not an omission. `RobotViewport` gained a real module-only rendering mode (`set_attached_module()`) that swaps out the normal robot/joint-chain draw path for a flat, non-animated segment list - checked and drawn BEFORE the robot registry lookup, so it never touches the existing per-robot rendering code. `ModuleConfigPanel` (the shared base behind `CncPanel`/`LaserPanel`/`HeatedBedPanel`/`VacuumTablePanel`) now embeds its own `RobotViewport` instance side by side with the settings form, matching STUDIO's own two-column layout, and keeps it live: enabling the module attaches the preview, disabling detaches it, and - a real gap caught while adding test coverage for this, not by inspection - editing the width/length spinbox now refreshes the preview immediately instead of waiting for the next state broadcast to round-trip back from the server, matching STUDIO's own reactive `<Canvas>` (`_on_size_changed()` now calls `_refresh_controls()` before pushing, not only after). The Pick & Place panel's own `juanenPnP`/`lumenPnP` preview is real GLB-mesh geometry on STUDIO's side (`LumenPnPRig.tsx`), a genuinely separate, larger piece of work (real mesh loading, not primitives) tracked apart from this pass, not silently faked here with a box. Real headless test coverage added to the existing `tests/verify_module_config_panel.py`: `RobotViewport.set_attached_module()`'s pending-rebuild cache path (attach/detach/an unported module key), and `ModuleConfigPanel` genuinely driving its own embedded viewport from real enable/width-change/disable state transitions - both passing, alongside the full existing suite and a full-tree `py_compile`.
- **Real live MJPEG video in the Cameras panel** - `iter_mjpeg_frames()` (new, `cameras_panel.py`) is a real client for the same proxied stream every camera card's metadata already pointed at: reads raw bytes off the wire and scans for JPEG SOI(0xFFD8)/EOI(0xFFD9) markers directly, the same real, proven approach `HYDRA-UMC-ANDROID-CONTROL`'s own `MjpegStreamParser.kt` uses (deliberately not parsing the multipart boundary/Content-Length headers - the marker scan works regardless of exact framing). Each camera card now starts a real `asyncio.Task` streaming `GET /api/camera/:id/stream` while connected, decoding each frame into a `QPixmap` and rendering it scaled into the card's own video area in place of the old LIVE/NO SIGNAL text; stops cleanly (task cancellation, not just a UI flip) on disconnect or when the camera leaves the roster. An oversized/corrupt frame (over the same real 1MB ceiling the Android parser uses) is silently skipped rather than killing the feed. Real headless test coverage (new `tests/verify_mjpeg_stream.py`: a real local HTTP server serving a real multipart stream, verifying exact byte-for-byte frame extraction, the oversized-frame-skip behavior, and a clean end when the server is unreachable - not mocked at the HTTP layer) plus the existing camera panel test suite and a full `MainWindow()` smoke construction - both passing. `README.md` (all 7 languages) and `docs/ROADMAP.md` updated to match - both had gone stale claiming this still didn't exist, caught during a real documentation audit pass, not just the feature work itself. Also fixed a real, separate bug found during that same pass: `README_jpn.md`'s own panel-count bullet had garbled, nonsensical text from an earlier hand-transcribed Unicode edit this same session, and `README_zho.md` had been skipped entirely in that earlier real-11/11-panel-count fix - both corrected now.
- **Tester panel - the 11th and LAST panel of the SUITE/STUDIO parity gap, now complete (11/11).** New `hydra_suite/ui/panels/tester_panel.py`: real port of STUDIO's own `Tester.tsx` (448 lines, the largest single file in this whole parity effort) - CAN-OTA runtime diagnostics for a Robot Controller Board or (relayed through it) a robot's own URTC Tool Head, porting URTC-TESTER's own feature set (global LED/OLED controls, F-RAM query/erase, per-tool telemetry, safe self-test, raw CAN bus monitor). Reuses `can_ota.py` in full (shared with Flasher, as intended when that module was built) - including `mock_bus_monitor()`, ported but unused until now. Target-selection block (Board/Robot Slot/hop description/Query Version) deliberately duplicates `flasher_panel.py`'s own rather than sharing a base class - STUDIO's own `Tester.tsx` does the exact same literal duplication against `Flasher.tsx` (both import the same `canOta.ts` helpers but never share a target-selection component), so mirroring that duplication is the more faithful port, not a shortcut. Confirmed and preserved a real, honest boundary: UNLIKE Flasher, only Query Version reaches a real hardware path here - self-test/F-RAM/LEDs/bus monitor all need real STM32H745 APPLICATION-level commands that don't exist in the H745 firmware yet (still a FreeRTOS smoke-test stub), so those stay simulated regardless of transport setting, with an explicit UI note rather than silently pretending otherwise. Status LED/Ring LED/OLED mode/F-RAM state are real-but-local UI state, matching STUDIO's own plain `useState()` for all four exactly (none of them round-trip through `push_active_state()` on STUDIO's own side either - no real command exists yet to send them anywhere). Real per-tool-category telemetry section (thermal/motor/vacuum/binary/generic, matching STUDIO's own `TOOL_CATEGORY` map). Self-Test runs `can_ota.py`'s own real `mock_self_test()` async generator end to end. Raw Bus Monitor Start/Stop drives a real `asyncio.Task` wrapping `mock_bus_monitor()`, genuinely cancelled on Stop (not just a UI state flip - verified in the test below that frames actually stop arriving after Stop, not just that the button text changes). `TesterPanel` takes the same `tiers` parameter as `FlasherPanel` and is instantiated TWICE in `main_window.py` ("Tester Center"/"Hardware Tester", matching STUDIO's own `Dashboard.tsx` nav labels exactly). No new `models.py` accessors needed - reuses everything `can_ota.py`/Flasher's own port already added. New `HEADING_TESTER`/`NAV_TESTER_CENTER`/`NAV_HARDWARE_TESTER`/`LBL_GLOBAL_CONTROLS`/`LBL_STATUS_LED`/`LBL_RING_LED`/`LBL_OLED_*`/`LBL_FRAM*`/`BTN_FRAM_*`/`LBL_TOOL_TELEMETRY`/`LBL_TELEMETRY_*`/`LBL_SELF_TEST*`/`BTN_RUN_SELF_TEST`/`LBL_SELFTEST_*` (10 step labels)/`LBL_BUS_MONITOR`/`BTN_MONITOR_*`/`LBL_COL_*` - 48 new keys × 7 languages, on top of reusing every Board/Robot-Slot/version key Flasher's own port already added. Real headless test coverage (new `tests/verify_tester_panel.py`: real per-tool category mapping, per-option tier gating for a robot both with and without URTC/expansion, urtcHead-only section visibility, real local-state Global Controls/F-RAM, a complete real `mock_self_test` run rendering real step results, and a real bus-monitor start/verify-frames-arrive/stop/verify-frames-actually-stop cycle - genuine cancellation, not a UI-only toggle) plus a full `MainWindow()` smoke construction - both passing, alongside `tools/ci_validate.py` and a full-tree `py_compile`.
- **Flasher panel** (new `hydra_suite/can_ota.py` + `hydra_suite/ui/panels/flasher_panel.py`) - the 10th of 11 still-pending panels from the SUITE/STUDIO parity gap, and by far the largest real port so far. `can_ota.py` is a full real port of STUDIO's own `src/lib/canOta.ts` (510 lines) - the shared CAN-OTA/SPI-OTA transport used by both this panel and the upcoming Tester one: real pure helpers (hop description, chip names, slot addressing), a real CRC32 (`zlib.crc32` - same IEEE 802.3 polynomial STUDIO's own hand-rolled table computes, verified against the textbook `"123456789"` -> `0xCBF43926` check value), the real `mock_flash`/`mock_query_version`/`mock_self_test` async generators (page-by-page progress, per-tier timing, the same real anti-rollback/random-offline simulation), real GitHub firmware manifest fetching (`firmware_manifest.json`, not the Releases API - see that file's own header for the real history), and the real hardware transport (`hardware_query_version`/`hardware_start_flash`) reaching HYDRA-UMC-SERVER's own `/api/hardware/canota/*` routes via a new `HydraConnection.canota_request()` (`net/client.py`) - kept separate from the existing `_request_json()` only because a flash POST sends a raw `application/octet-stream` body, not JSON. `resolve_hardware_target()` reproduces STUDIO's own honest boundary exactly: Tier 3 (urtcExpansion) has no real tunnel hop yet and stays unreachable regardless of transport setting. `FlasherPanel` takes a `tiers` parameter and is instantiated TWICE in `main_window.py` (`URTC_TIERS`/`HYDRA_BRAIN_TIERS`), matching STUDIO's own `Dashboard.tsx` exactly (its "Flasher Studio" and "Firmware Update" nav entries are the same component with different tier sets, not two different components) - Board select with real per-option gating (urtcHead disabled when that robot's own `urtcConnected` is false, urtcExpansion disabled when `hasAdvancedExpansion()` says no), Robot Slot select (hidden for the robot-independent kinematicBrain tier), live hop-description readout, Query Version, firmware file loading (`QFileDialog` browse or GitHub manifest download with a real CRC32 verify against the manifest's own value), Allow Downgrade / Erase F-RAM options, Flash Now with a confirm dialog and a real progress bar driven either by the mock generator or (for `transport === 'hardware'`, Tier 0-1 only) the real HTTP call. New `ControllerView.kinematic_brain`/`set_kinematic_brain()` (the board's own firmware/identity record - deliberately distinct from `kinematic_brain_stage`, its LIVE gantry/bed/etc. state) and `RobotView.urtc_connected` accessors, plus `HydraState.can_ota_transport` (reads `settings.canOta.transport`, defaulting to `"mock"` exactly like STUDIO's own strict-equality check) on `models.py` - `controllerBoard`/`urtcHead`/`urtcExpansion` board state reuses the EXISTING generic `module()`/`set_module()` accessors, no new ones needed for those three. New `HEADING_FLASHER`/`NAV_FLASHER_STUDIO`/`NAV_FIRMWARE_UPDATE`/`LBL_BOARD`/`LBL_TARGET_*`/`LBL_ROBOT_SLOT`/`BTN_QUERY_VERSION`/`LBL_FIRMWARE_FILE`/`BTN_BROWSE_BIN`/`BTN_DOWNLOAD_GITHUB`/`LBL_ALLOW_DOWNGRADE`/`LBL_ERASE_FRAM`/`BTN_FLASH_NOW`/`MSG_CONFIRM_FLASH`/`FLASHER_PROGRESS_*` (all 8 phases) and more - 43 new keys × 7 languages. Real headless test coverage (new `tests/verify_can_ota.py`: pure helpers, the real CRC32 check value, `resolve_hardware_target`'s own Tier 3 boundary, and full real runs of `mock_query_version`/`mock_flash`/`mock_self_test` - not stubbed; new `tests/verify_flasher_panel.py`: per-option tier gating for both a robot with and without URTC/expansion, the kinematicBrain-vs-controllerBoard robot-slot visibility difference, real board-state display, and a complete real `mock_flash` cycle run through the panel's own actual `_do_flash()` path, ending with the board state genuinely patched) plus a full `MainWindow()` smoke construction - both passing, alongside `tools/ci_validate.py` and a full-tree `py_compile`.
- **Kinematic Brain Stage panel** (new `hydra_suite/ui/panels/kinematic_brain_stage_panel.py`) - the 9th of 11 still-pending panels from the SUITE/STUDIO parity gap. Control panel for the Kinematic Brain's OWN local 6-axis stage (STM32H745): X/Y1/Y2 dual-Y XY gantry, Z table/head height, E0 ATC revolver index, E1 conveyor (wired, not yet a built feature). UNLIKE every panel in this family so far, this is CONTROLLER-level state (`ControllerView.kinematic_brain_stage`), not per-robot - there is exactly one Kinematic Brain per controller, so this panel has no robot selector at all. Real XY gantry jog (7-step selector, X/Y1/Y2/Z buttons clamped to table bounds, live readout) + table width/length/height; heated bed (2 read-only thermistors, target temp, SSR toggle); ATC revolver (prev/next step with real modulo wraparound, tool-slot count, homed indicator); conveyor (install-gated running/stopped toggle + speed slider); 12 endstops (2 per axis); 3 fans, 10 pumps, 10 valves, each independently toggleable. New `ControllerView.kinematic_brain_stage`/`set_kinematic_brain_stage()` accessors plus a module-level `default_kinematic_brain_stage()` helper on `models.py`, matching STUDIO's own `createDefaultKinematicBrainStage()` real seed values exactly (600×400×150mm table, 6-slot revolver, etc.) - returned when the field is genuinely absent, same "never actually missing in practice" reasoning as the Rack Manager port, even though STUDIO's own component would render nothing at all in that edge case (`if (!activeController || !stage) return null`, no "Enable" affordance anywhere for this one). New `HEADING_KINEMATIC_BRAIN_STAGE`/`LBL_GANTRY`/`LBL_HEIGHT_Z`/`LBL_ATC_REVOLVER_E0`/`LBL_TOOL_COUNT`/`LBL_HOMED`/`LBL_NOT_HOMED`/`LBL_CONVEYOR`/`LBL_CONVEYOR_NOT_INSTALLED`/`BTN_MARK_INSTALLED`/`LBL_RUNNING`/`LBL_STOPPED`/`LBL_ENDSTOPS`/`LBL_FANS`/`LBL_PUMPS`/`LBL_VALVES` keys × 7 languages (reusing existing generic `LBL_STEP`/`LBL_WIDTH_X`/`LBL_LENGTH_Y`/`HEADING_HEATED_BED`/`LBL_THERMISTOR_1`/`LBL_THERMISTOR_2`/`LBL_TARGET_TEMP`/`BTN_SSR_ON`/`BTN_SSR_OFF` keys for everything already shared with other panels - `LBL_ATC_REVOLVER_E0` deliberately NOT reusing the existing `LBL_ATC_REVOLVER` key, which already means the plain word "Revolver" as an ATC type-option label elsewhere and would have been wrong here). Real headless test coverage (new `tests/verify_kinematic_brain_stage_panel.py`: field round-trip including the "missing field doesn't get silently written back" check, XY jog with clamping, heated bed, ATC step with real modulo wraparound, conveyor install/run/speed, and independent endstop/fan/pump/valve toggles) plus a full `MainWindow()` smoke construction - both passing, alongside `tools/ci_validate.py` and a full-tree `py_compile`.
- **Pick & Place config panel** (new `hydra_suite/ui/panels/pick_and_place_panel.py`) - the 8th of 11 still-pending panels from the SUITE/STUDIO parity gap. NOT built directly on `ModuleConfigPanel`: unlike CNC/Laser (one module key per panel instance), this ONE panel switches between TWO real module keys (`juanenPnP`/`lumenPnP`) via its own in-panel Machine combo, reusing `RobotView.module()`/`module_enabled()`/`set_module()`'s existing generic accessors directly rather than instantiating `ModuleConfigPanel` twice. Confirmed and preserved a real observation from STUDIO's own source: `isPnpMachine` is always `true` given the Machine combo only ever offers those two values, so its own plain width/length branch (same shape as CNC/Laser) is real but currently unreachable - ported anyway rather than collapsed away, in case a 3rd machine type is ever added on either side. The reachable PnP branch is a manual pose-preview control (5 sliders - X/Y/Z axis position plus 2 nozzle rotations) using STUDIO's own real fixed hardware bounds (433mm/487mm/90mm travel, ±180° rotation) - no live firmware feed for either PnP machine exists anywhere in the ecosystem yet, matching that file's own comment. Reset writes size defaults AND all 5 axis fields to 0 in one call, matching `handleReset()` exactly. New `HEADING_PICK_AND_PLACE`/`LBL_MACHINE`/`LBL_PNP_POSE_PREVIEW`/`LBL_PNP_AXIS_X`/`LBL_PNP_AXIS_Y`/`LBL_PNP_AXIS_Z`/`LBL_PNP_NOZZLE1`/`LBL_PNP_NOZZLE2` keys × 7 languages (reusing existing generic module keys for everything else). No new `models.py` accessors needed - the existing generic `module()` family already covered this shape. Real headless test coverage (new `tests/verify_pick_and_place_panel.py`: default machine, enable, PnP axis edits, reset, and - the real risk this shape introduces - that switching machines and editing one never leaks into the other's own stored data) plus a full `MainWindow()` smoke construction - both passing, alongside `tools/ci_validate.py` and a full-tree `py_compile`.
- **Rack Manager config panel** (new `hydra_suite/ui/panels/rack_config_panel.py`) - the 7th of 11 still-pending panels from the SUITE/STUDIO parity gap. NOT built on `ModuleConfigPanel`: `rackSystem` nests two real sub-racks (rack1/rack2, each its own type/capacity/usableSlots/basePickupPos), a shape none of that family's single-module panels have. `rackSystem` itself is never undefined on the TypeScript side (unlike `atc`/`xyTable`) - `RobotView.rack_system` returns the same real seed default STUDIO's own `createDefaultRobots()` uses when genuinely absent, rather than crashing on an edge case STUDIO's own source (no optional chaining on `selectedRobot.rackSystem.enabled`) doesn't defend against either. Faithfully reproduces a real, easy-to-miss quirk instead of fixing it here: each rack's own Reset button does NOT reference its own `rackId` in STUDIO's source - clicking Reset on EITHER rack always resets BOTH rack1 and rack2 together (and force-enables the system). Real per-rack type select (None/Input/Output), capacity slider (1-24), a usable-slots grid, and a base pickup position editor (6 joints + table tx/ty, gated on `hasXYTable` same as XY Table/ATC). New `RobotView.rack_system`/`set_rack_system()` accessors plus module-level `default_rack()`/`default_rack_system()` helpers on `models.py`. New `HEADING_RACK_MANAGER`/`LBL_RACK1`/`LBL_RACK2`/`LBL_RACK_TYPE`/`LBL_DISABLED`/`LBL_INPUT_RACK`/`LBL_OUTPUT_RACK`/`LBL_CAPACITY`/`LBL_USABLE_SLOTS`/`LBL_BASE_PICKUP_POS` keys × 7 languages (reusing the existing generic `BTN_RESET_MODULE`/`LBL_NO_MODULE_ASSIGNED`/`BTN_ENABLE_MODULE`/`BTN_REMOVE_MODULE` keys - `BTN_REMOVE_MODULE`'s existing "Remove Module" text is what STUDIO's own `RackConfigView.tsx` actually renders too, despite its own source literally saying `t('modules.remove_module', 'Remove Rack')` - the inline `'Remove Rack'` fallback never fires since the `modules.remove_module` key is already defined as "Remove Module" in every real locale file, confirmed by reading STUDIO's own `en.json`). No live 3D preview to omit here - `RackConfigView.tsx` itself has none either. Real headless test coverage (new `tests/verify_rack_config_panel.py`: field round-trip including the "missing rackSystem doesn't get silently written back" check, empty state, enable, type/capacity/slot edits including padding a short `usableSlots` array on an out-of-range toggle, base pickup position edits, the both-racks-reset-together quirk, disable) plus a full `MainWindow()` smoke construction - both passing, alongside `tools/ci_validate.py` and a full-tree `py_compile`.
- **XY Table config panel** (new `hydra_suite/ui/panels/xy_table_panel.py`) - the 6th of 11 still-pending panels from the SUITE/STUDIO parity gap. NOT built on `ModuleConfigPanel`: STUDIO keeps `hasXYTable: boolean` and `xyTable: {...}` as two genuinely separate fields (unlike every `ModuleConfigPanel`-family module's single `{enabled, size}` shape, and unlike ATC's own "presence of the key is the state" shape too). Faithfully reproduces a real quirk this surfaced: STUDIO's own `handleJog()`/`handleSizeChange()` both no-op until a real `xyTable` object exists - only `handleReset()` unconditionally creates one, so Enable then Reset is the real required sequence before jog/size do anything; also reproduces the same kind of two-different-defaults quirk found in the Vacuum Table port (display fallback 500mm vs. the 300mm `handleReset()` actually writes) rather than collapsing either one. Real robot selector, size (width/length mm), a manual jog control (7-step selector from 0.01mm to 100mm, X/Y jog buttons clamped to table bounds, live position readout), Reset, Remove, and Save Config (`QFileDialog` JSON export, matching STUDIO's own `saveConfig()` - no Load, since STUDIO's own source has none either). New `RobotView.xy_table`/`set_xy_table()`/`set_has_xy_table()` accessors on `models.py`. New `HEADING_XY_TABLE`/`GROUP_JOG_CONTROL`/`LBL_STEP` keys × 7 languages (reusing the existing generic `BTN_RESET_MODULE`/`LBL_NO_MODULE_ASSIGNED`/`BTN_ENABLE_MODULE`/`BTN_REMOVE_MODULE`/`LBL_WIDTH_X`/`LBL_LENGTH_Y`/`BTN_SAVE_CONFIG`/`GROUP_MODULE_SETTINGS` keys the other module panels already share). Same live-3D-preview omission as the rest of this family. Real headless test coverage (new `tests/verify_xy_table_panel.py`: field round-trip, empty state, enable-writes-flag-only, size/jog no-op before Reset, Reset default vs. display default, size/jog write-back with clamping, disable-keeps-data) plus a full `MainWindow()` smoke construction - both passing, alongside `tools/ci_validate.py` and a full-tree `py_compile`.
- **Cameras panel: real IP (RTSP) camera support + Assigned Robot** (`hydra_suite/ui/panels/cameras_panel.py`) - the SUITE-side port of the real Source Type toggle just added to HYDRA-UMC-STUDIO's own `Config.tsx`/`CamerasView.tsx` (see that repo's own CHANGELOG), per the standing "every STUDIO novelty gets a SUITE equivalent" rule. Each camera card now has a real Assigned Robot dropdown (previously not exposed in SUITE at all) and a USB/IP Camera toggle: USB mode keeps the existing Hardware Source field (previously also missing from this panel - `/dev/video0` style path), IP mode adds real, generic RTSP fields - Host/IP Address, RTSP Port (spin box, defaults to 554), RTSP Path, Username, Password - deliberately not tied to any one camera brand, matching `HYDRA-UMC-VISION-STREAMER`'s own `CameraConfig(source_type=...)` field for field. New `CameraView.assigned_robot_id`/`source_type`/`hardware_source`/`ip_host`/`rtsp_port`/`rtsp_path`/`ip_username`/`ip_password` accessors on `models.py` (`RTSP_DEFAULT_PORT = 554` constant), all optional so every existing saved camera entry keeps working unchanged (`source_type` undefined reads as `"usb"`, same as STUDIO). `assigned_robot_id` is written back as a real JSON number, not a string - STUDIO's own robot-toggle path does a strict `===` comparison against it. New `LBL_ASSIGNED_ROBOT`/`OPT_NONE_FLOATING`/`LBL_SOURCE_TYPE`/`BTN_SOURCE_USB`/`BTN_SOURCE_IP`/`LBL_HARDWARE_SOURCE`/`LBL_IP_HOST`/`LBL_RTSP_PORT`/`LBL_RTSP_PATH`/`LBL_IP_USERNAME`/`LBL_IP_PASSWORD` keys across all 7 languages. Real headless test coverage (new `tests/verify_cameras_panel.py`: `CameraView` field-by-field round trip including the int-not-string assertion on `assigned_robot_id`, plus real `CamerasPanel` widget wiring - card creation from real state, Source Type page switching, robot-combo population, and field edits round-tripping through the panel's own real callback path) - passing, alongside the repo's real CI checks (`tools/ci_validate.py`, full-tree `py_compile`).
- **ATC (Automatic Tool Changer) config panel** (new `hydra_suite/ui/panels/atc_tools_panel.py`) - the 5th of 11 still-pending panels from the SUITE/STUDIO parity gap, and the first NOT built on `ModuleConfigPanel` (STUDIO's own `selectedRobot.atc` is a fundamentally different shape than every other module: `undefined` when unconfigured, a full `ATCConfig` object otherwise, no separate `enabled` flag - see that file's own header for why sharing the base class would have meant inventing fields STUDIO doesn't have). Real port of STUDIO's `ATCToolsConfig.tsx` (465 lines): 3 real layout modes (vertical panel, horizontal panel, revolver), the same 25-item real URTC tool catalog per slot (kept untranslated, matching STUDIO's own source, which never wraps these in `t()` either), a real 6-joint + optional table-XY position editor per slot and for the revolver's own base pickup position, JSON export/import of the whole config (`QFileDialog`, first use of it in this app), and a real graphic representation - a grid of slots or a circular revolver layout - built from scratch with `QPainter` (`AtcGraphicsWidget`), matching STUDIO's own from-scratch CSS/div graphic 1:1 in structure. New `RobotView.atc`/`set_atc()`/`has_xy_table` accessors on `models.py` (deliberately separate from `module()`/`module_enabled()`, whose `{enabled: bool, ...}` shape doesn't fit this one). New `HEADING_ATC`/`LBL_ATC_*`/`BTN_EDIT_POS`/`LBL_TOOL_ASSIGNMENTS`/`BTN_LOAD_CONFIG`/`BTN_SAVE_CONFIG`/`MSG_ATC_INVALID_CONFIG` keys × 7 languages (reusing the existing generic `BTN_RESET_MODULE`/`LBL_NO_MODULE_ASSIGNED`/`BTN_ENABLE_MODULE`/`BTN_REMOVE_MODULE` keys the other module panels already share, parameterized with `machine="ATC"`, rather than duplicating them). Also corrected a stale `CameraView` docstring claiming no real camera hardware/stream exists anywhere in this ecosystem - real as of today (`HYDRA-UMC-VISION-STREAMER`'s own `stream serve`, proxied through `HYDRA-UMC-SERVER`'s `GET /api/camera/:id/stream`, verified end to end against a real USB webcam); a real live viewport for it in this app (matching STUDIO's own CameraPIP) is still separate, not-yet-done work, tracked honestly rather than left implying a hardware limitation that no longer exists. Real headless test coverage (new `tests/verify_atc_tools_panel.py`: `atc`/`set_atc`/`has_xy_table` round-trip, enable/tool-assignment/position-edit/grid-change/type-switch/reset/remove, and the `hasXYTable` gate on the position editor's table fields) plus a full `MainWindow()` smoke construction - both passing. Same live-3D-preview omission as the rest of this family (`render/viewport.py` has no attached-module geometry support yet) - the 2D graphic representation above is a full, real port, not a placeholder for it.
- **Vacuum Table tool-attachment config panel** (new `hydra_suite/ui/panels/vacuum_table_panel.py`, docked next to CNC/Laser/Heated Bed) - the 4th of 11 still-pending panels from the SUITE/STUDIO parity gap. Adds a real Pump on/off toggle and a real Valve open/closed toggle via `ModuleConfigPanel`'s extension hooks. Also fixed a real inconsistency this panel surfaced: STUDIO's own `VacuumTableConfig.tsx` displays a 500mm width/length fallback on enable (same as CNC/Laser/HeatedBed) but its own `handleReset()` writes 100mm instead - two different numbers for the same module. `ModuleConfigPanel`'s single size-default hook was split into `_display_default_size_mm()` (enable-time UI fallback, unchanged at 500 for every module) and `_reset_size_mm()` (the value Reset actually writes, 500 for CNC/Laser/HeatedBed, 100 for VacuumTable) so this real quirk is reproduced faithfully instead of silently picking one of the two numbers. Also stopped `_on_enable()` from persisting a `size` default at all (STUDIO's own `handleToggle()` doesn't either - it writes only `enabled`), matching the source exactly; CNC/Laser/HeatedBed's own display behavior is unaffected since 500 is still what the fallback shows. New `HEADING_VACUUM_TABLE`/`GROUP_VACUUM_CONTROLS`/`BTN_PUMP_ON`/`BTN_PUMP_OFF`/`BTN_VALVE_OPEN`/`BTN_VALVE_CLOSED` keys × 7 languages. Real headless test coverage extended in `tests/verify_module_config_panel.py` (enable persists no size, pump/valve write-back, reset writes the module's own 100mm default) plus a full `MainWindow()` smoke construction - both passing.
- **Heated Bed tool-attachment config panel** (new `hydra_suite/ui/panels/heated_bed_panel.py`, docked next to CNC/Laser) - the 3rd of 11 still-pending panels from the real, standing SUITE/STUDIO parity gap. Ports STUDIO's own `HeatedBedConfig.tsx` on top of the existing `ModuleConfigPanel` (robot selector, enable/disable, width/length, reset) via 4 new extension hooks on that shared base class (`_build_extra_settings`/`_refresh_extra_controls`/`_extra_default_fields`/`_extra_reset_fields`, no-ops for CNC/Laser) rather than duplicating the shared shape a third time: a real SSR on/off toggle, a user-set target temperature, and two read-only thermistor readouts (`currentTemp1`/`currentTemp2` - live telemetry fields this panel displays, never simulates). New `HEADING_HEATED_BED`/`GROUP_HEATING_CONTROLS`/`LBL_TARGET_TEMP`/`LBL_THERMISTOR_1`/`LBL_THERMISTOR_2`/`BTN_SSR_ON`/`BTN_SSR_OFF` keys across all 7 languages. Same live-3D-preview omission as CNC/Laser (`render/viewport.py` has no attached-module geometry support yet). Real headless test coverage extended in `tests/verify_module_config_panel.py` (enable defaults, target-temp/SSR write-back, reset, and rendering real live telemetry from state) plus a full `MainWindow()` smoke construction - both passing.
- **Real About dialog**, matching HYDRA-UMC-STUDIO's own `About.tsx`: the
  single-line `QMessageBox` is now a proper `AboutDialog` with the animated
  logo, a colored HYDRA-UM-C wordmark, a tagline, a one-paragraph
  description, and real Version/Author/Email/License rows (email is a
  clickable `mailto:` link). New `ABOUT_TAGLINE`/`ABOUT_DESCRIPTION`/
  `ABOUT_VERSION`/`ABOUT_AUTHOR`/`ABOUT_EMAIL`/`ABOUT_LICENSE`/`BTN_CLOSE`
  keys across all 7 languages, replacing the old single `MSG_ABOUT_BODY`
  string - full key parity verified across every language file.
- **Fixed: command deck rendered as a blank black bar.** A later revision
  moved the command deck into a `QQuickWidget`/QML island (matching
  HYDRA-UMC-UPDATER's own renderer) - real per-project screenshots showed
  it painting solid black in this QMainWindow, every time, with no console
  error: a `QQuickWidget` embedded inside a `QToolBar` inside a real
  `QDockWidget`-based main window never got a correctly composited native
  surface, even though the identical QML renders perfectly in UPDATER -
  because UPDATER is a pure `QQmlApplicationEngine` window with no
  competing widget tree around it, not a `QMainWindow` with dockable
  panels. Reverted the deck to plain `QToolBar`/`QLabel`/`QToolButton`
  widgets (the original, working implementation) - real per-project
  screenshots now confirm the logo, title, navigation buttons and status
  chips all render correctly. The orphaned QML/bridge files were moved
  out of the repo rather than deleted.
- **Fixed: Robot Control's own Joints clipped under the default dock
  split.** The top row (Servers/Overview/3D Viewport/Robot Control) and
  the bottom tab group shared height roughly 50/50 by default, which cut
  off Robot Control's own J5/J6 sliders and the Playback/Acceleration
  controls below them - real screenshots confirmed it. The top row now
  gets a real, explicit majority of the vertical space via
  `resizeDocks(..., Qt.Orientation.Vertical)`, same mechanism already
  used for the Viewport/Robot Control horizontal split.
- **Visual command deck**: added a persistent top-level command surface that
  raises Suite's real Overview, Robot Control, Cameras, Trajectory and Logs
  docks. It reports the actual active connection state, selected target and
  UTC clock rather than showing hard-coded operational data.
- **Unified ecosystem visual language**: refreshed the industrial Qt style
  with the deep-navy, cyan and readable technical-control palette established
  by HYDRA-UMC-UPDATER. Added the official HYDRA-UMC SVG/ICO mark for the
  window, taskbar and command deck (the deck's own logo is a real, animated
  `QSvgWidget` over the source SVG, not a static bitmap). The
  source SVG and reproducible ICO remain first-class project assets. The QSS
  now uses the same 16px section shells, 11px metric cards and 10px interactive
  controls as the Updater command deck.
- Added the command-deck labels to all seven Suite language files and
  synchronized the public README languages with the real visual behavior.

## [0.3.8]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.3.7]

- **Setup Camera now shows one real, editable path field per discovered
  stream** - STUDIO/SUITE parity, same real bug found via live user
  testing: a camera whose last "Discover Path" run found 2+ real
  streams had nowhere to show/edit the 2nd one, only the primary
  `rtsp_path` field existed. `CameraCard` now shows up to 3 extra
  labelled, editable fields (real hardware in this ecosystem has never
  shown more than 2, so a small fixed pool rather than fully dynamic
  Qt layout mutation) - editing the field matching the CURRENTLY
  selected stream also updates the live `rtsp_path`, editing another
  just updates its own stored path for when that stream gets selected
  later. A fresh discovery still autofills every field it found.
- **Switching streams in the type combobox now reconnects immediately**,
  instead of waiting for whatever incidental state broadcast happens to
  trigger the next `refresh()` - real behavior parity with the
  underlying bug HYDRA-UMC-STUDIO's own CamerasView.tsx had (its own
  fix: see that repo's CHANGELOG). `_on_type_combo_changed()` now stops
  and restarts this card's own MJPEG stream task the moment `rtsp_path`
  actually changes, rather than leaving the old frame on screen until
  something else happens to refresh it.
- Real assertion coverage extended in `tests/verify_cameras_panel.py`
  for the extra path fields (visibility, autofill, and that editing the
  active vs. an inactive one has the right effect on the live
  `rtsp_path`). Full existing suite unaffected (every other
  `verify_*.py` still passes).

## [0.3.6]

- **Stopped is a real status now, not a red "error" badge** - the
  client half of HYDRA-UMC-SERVER's fix for a real bug: a camera
  toggled off used to leave its real capture process alive, silently
  burning CPU/memory (see that repo's own CHANGELOG). Now that the
  server genuinely stops that process and reports a real `"stopped"`
  status, `CameraCard`'s own badge shows it in its own neutral grey
  (new `STATUS_STREAM_STOPPED` key × 7 languages) instead of falling
  back to a raw, untranslated `"STOPPED"` string in the red error
  color a status it didn't recognize used to get.

## [0.3.5]

- **Real multi-stream RTSP support - STUDIO/SUITE parity.** A real IP
  camera on this ecosystem's own network can expose more than a fixed
  Main/Sub pair - HYDRA-UMC-SERVER's own `discoverRtspPath()` used to
  stop scanning at the first candidate that answered, so a camera with
  2+ real streams only ever surfaced whichever one happened to be
  tried first (see that repo's own CHANGELOG). New `models.py`'s
  `ip_stream_labels()` (mirrors HYDRA-UMC-STUDIO's own `ipStreamLabels()`
  exactly) derives the real option list from a camera's own new
  `discovered_stream_paths` field: 1 stream -> Main only, 2 -> Main/Sub,
  3+ -> Main/Sub Stream 1/Sub Stream 2/... `CameraCard`'s own type
  combobox now builds its IP options from this instead of the old fixed
  pair - picking a different one is a real behavior change, not just a
  label: it re-points that camera's own `rtsp_path` at the corresponding
  discovered stream, which the server's own process supervisor picks up
  and respawns the real capture for. A fresh "Discover Path" run now
  records the FULL found list, not just the first, and resets the
  selection to Main by default. Real assertion coverage extended in
  `tests/verify_cameras_panel.py` for the 2-stream and 3-stream cases
  (dynamic option lists, and that selecting a numbered Sub option
  actually switches `rtsp_path`).

## [0.3.4]

- **Camera discovery + real live status - STUDIO/SUITE parity.** Mirrors
  HYDRA-UMC-STUDIO's own Config.tsx additions for HYDRA-UMC-SERVER's new
  camera-process supervisor (`reconcileCameraProcesses()`,
  `GET /api/cameras/status`, `POST /api/camera/discover-rtsp-path`,
  `GET /api/camera/discover-usb-devices` - see that repo's own
  CHANGELOG). `CameraCard` (`cameras_panel.py`) gets a real per-camera
  status badge (polled every 3s, running/starting/error color-coded,
  real `lastError` in the tooltip), a "Discover USB Devices" button
  (lists real indices the server's own `cv2.VideoCapture` probe found,
  picking one fills `hardwareSource` with the real platform-correct
  value - a bare index on Windows, `/dev/videoN` on Linux/CM5), and a
  "Discover Path" button for IP cameras (tries this ecosystem's own
  known-real RTSP paths server-side, never invents one, reports exactly
  which ones were tried on failure). No separate "Apply" button needed
  here - unlike STUDIO's own 500ms-debounced save, this app's
  `push_active_state()` already writes on every field edit immediately.
  New `HydraConnection.fetch_camera_status()`/`discover_rtsp_path()`/
  `discover_usb_devices()` follow the existing `_request_json()`-
  delegating one-liner pattern.
- **Type combobox now context-sensitive to source type.** `CAMERA_TYPES`
  gained `"IP Vision Camera Main Stream"`/`"IP Vision Camera Sub Stream"`
  (a real IP camera in this ecosystem can expose 2 real RTSP streams at
  once) alongside the existing `"USB Vision Camera"` and the 3 Thermal
  options (left unconditional - no thermal-sensor functionality yet).
  `CameraCard`'s own type combobox now only offers the pair matching the
  camera's real `sourceType` (mirrors HYDRA-UMC-STUDIO's own
  `CamerasView.tsx` combobox split) instead of always listing all
  options - a `type` value no longer valid for the current
  `sourceType` falls back to that list's own first entry rather than
  leaving Qt's combobox in a blank/mismatched state. Toggling source
  type (USB <-> IP) auto-normalizes a stale `type` label the same way
  Config.tsx's own onClick handlers do, leaving a Thermal selection
  untouched either way.
- Real assertion coverage added to `tests/verify_cameras_panel.py` for
  all of the above (combobox context-sensitivity across both directions
  of the source-type toggle, the Thermal-survives-a-toggle case, the
  status badge, and both discovery round trips against a fake
  `HydraConnection`) - all passing, plus the full existing suite
  unaffected. `npx`-equivalent `tsc`/build not applicable here; ran
  every `tests/verify_*.py` and `smoke_test_app.py` in this repo's own
  `.venv` with no regressions.

## [0.3.3]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.3.2]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.3.1]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.3.0]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.2.9]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.2.8]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.2.7]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.2.6]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.2.5]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.2.4]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.2.3]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.2.2]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.2.1]

- **CNC and Laser tool-attachment config panels** (new `hydra_suite/ui/panels/cnc_panel.py`/`laser_panel.py`, docked next to the existing Ecosystem/Admin panels) - the first 2 of 11 still-pending panels from the real, standing gap between SUITE and HYDRA-UMC-STUDIO's own per-tool config screens. STUDIO's own `CNC.tsx`/`Laser.tsx` are byte-for-byte identical components aside from the module key/heading/icon, so both are backed by one shared implementation, `ui/panels/module_config_panel.py`'s `ModuleConfigPanel`: a robot selector, a real empty state when no module is configured yet, enable/disable, width/length (mm) size fields, and a reset action - all writing through `SuiteController.push_active_state()`, matching STUDIO's own `updateRobot()` full-tree write.
- **`RobotView.module()`/`module_enabled()`/`set_module()`** (new, `hydra_suite/models.py`) - a generic accessor for any tool-attachment's own config block (`juanenCNC`, `juanenLaser`, and future ones), mirroring STUDIO's own generic `selectedRobot[machineType]` indexing instead of a hardcoded property per module.
- Deliberately does **not** port `CNC.tsx`/`Laser.tsx`'s own right-hand live 3D preview (a react-three-fiber `<Canvas>`) - SUITE's own 3D viewport (`render/viewport.py`) is a from-scratch renderer with no existing support for an attached tool module's own geometry, and building that is real, separate work. The functional config surface (enable/disable, size, reset) is unaffected.
- Real headless test coverage: `tests/verify_module_config_panel.py` (constructs real Qt widgets, feeds a real `HydraState` through `SuiteController.active_state_changed`, asserts on the enable/size-change/disable/reset round-trip and that `CncPanel`/`LaserPanel` each read their own module key independently). `python tools/ci_validate.py`: PASS.

## [0.2.0] - Ecosystem Services panel reaches parity with STUDIO's own 0.3.7

- **`EcosystemServicesPanel` brought up to STUDIO's `EcosystemServices.tsx`
  0.3.7 feature set** - real request: keep SUITE's own menus/panels
  functionally similar to STUDIO's, its real difference being that SUITE
  can hold several `HydraConnection`s at once and switch which one is
  active (`SuiteController.connections`), where STUDIO only ever talks
  to the one Server it's loaded from. Added: the same 5-state health
  color (green=running, red=stopped, amber=a real error - systemd's own
  `ActiveState: "failed"`, or "active" yet its own declared port probes
  down - slate=N/A), the version shown large inside the status badge,
  real host:port/PID chips (`serviceHost`/`servicePort` from a port
  probe, `pid` from an opt-in `service.systemd_unit` probe,
  independent signals), 4 new stat tiles (Running/Stopped/Error/N/A)
  alongside Total/Live/Families, and admin-only Start/Stop/Restart
  buttons per card (only for a project that declares
  `service.systemd_unit`) calling HYDRA-UMC-SERVER's own
  `POST /api/ecosystem/service/:unit/:action` (see that repo's own
  `[0.3.7]`) - Stop/Restart confirm first via `QMessageBox`, Start
  fires immediately, only the acting card's own buttons disable while
  in flight. New `HydraConnection.control_service()` in `client.py`.
- **`AdminLogsPanel` gets a real Clear button**, same "remember the
  newest line at the moment Clear was pressed, only show what comes
  after it in later polls" behavior as STUDIO's own `AdminLogs.tsx` -
  unlike that React component, this panel is a real `QWidget` kept
  alive for the app's whole lifetime (built once in `main_window.py`,
  shown/hidden on tab switch, never torn down), so a plain instance
  attribute already survives navigation with no extra state-lifting
  needed.
- Updated the panel's own stale footer note (still said start/stop was
  "not built yet").
- `BTN_CLEAR` and 20 new service-status/action keys added to all 7
  language files.

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
