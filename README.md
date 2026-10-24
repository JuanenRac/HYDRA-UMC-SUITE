<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-SUITE banner" width="100%">
</p>

# 🧰 HYDRA-UMC SUITE

<p align="center">
  🇺🇸 <b>English</b> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>


### 🖥️ Multi-Controller Swarm Command Center for the HYDRA-UMC Platform

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.12-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="PySide6">
  <img src="https://img.shields.io/badge/Graphics-OpenGL-5586A4.svg" alt="OpenGL">
</p>


**Honesty check - what actually runs today:** network discovery (concurrent subnet scan + real mDNS/Bonjour, `hydra_suite/net/discovery.py`), the live REST+WebSocket connection and swarm support (`hydra_suite/net/client.py`, `hydra_suite/app.py`), the 3D viewport's real forward kinematics for all 24 real robot models plus a primitive "Generic" fallback (`hydra_suite/render/`, numerically verified bit-for-bit against HYDRA-UMC STUDIO's own TypeScript FK), all 11 of 11 tool-attachment config panels, CAN-OTA/SPI-OTA flashing, and real MJPEG camera rendering are real and tested - 39 offline verify/smoke scripts under `tests/` (`python tools/run_offline_verifiers.py`, headless Qt via `QT_QPA_PLATFORM=offscreen`), all passing. The interface is Qt Quick only (`qt_suite.py`): all 32 panels of the navigation are real, working code, including the 3D viewport through a dedicated `OffscreenRobotRenderer`; the classic window was removed. What is explicitly NOT done yet, per this repo's own honesty convention: the URTC Tool Head/Advanced Expansion CAN-OTA tiers have no real hardware relay tunnel; and `combinedWith` (combined-robot mode) isn't exposed in this app's UI despite existing in STUDIO's own data model. The Trajectory panel now exports/imports through HYDRA-UMC STUDIO's own real `WORKS/*.json` format (`POST /api/upload-work`, `GET /<folder>/index.json`) - a point recorded here is a real, playable Work from either app. See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the complete, itemized real-vs-deferred breakdown this paragraph summarizes, and `CHANGELOG.md` for exactly what has shipped so far.

---

> **Safety and security status:** this ecosystem is not a certified safety system. There is no hardware E-STOP path, no firmware-enforced limits or interlocks and no verified motion command yet; firmware images are checked with CRC32 and a shared-key HMAC-SHA256, not with an asymmetric signature; TLS and mutual TLS are optional and off by default; no custom board has been populated or tested yet. Read the [security baseline](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) and the [threat model](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) before relying on any statement here for the safety of a person.

## 📋 At a glance

| | |
|---|---|
| Version | `0.7.0` |
| Maturity | Functional |
| Stack | Python 3.12 / PySide6 |
| Target | The PC of the person using it |
| On real hardware | Not yet: no run on real hardware is recorded for this version |

## 🎯 Overview

**HYDRA-UMC SUITE** is a native Windows/Linux desktop application (Python
+ PySide6/Qt6) built as a mission-control center for a whole fleet of
[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) controllers at once -
scan the local network (or add one manually, including through an
already-connected VPN tunnel to a HYDRA-UMC on a different physical
network), connect to as many as are found, and jog/monitor/reconfigure
any of them live, side by side, from one fullscreen industrial dashboard.

It speaks the exact same wire protocol
[HYDRA-UMC SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER) exposes -
the same headless backend [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)'s
own browser UI talks to as just another client of it - see
[`HYDRA-UMC-SERVER/docs/REMOTE_API.md`](https://github.com/JuanenRac/HYDRA-UMC-SERVER/blob/main/docs/REMOTE_API.md)
for the full contract, added specifically to support this project. A
change made from SUITE shows up live in an open browser tab, and vice
versa - real bidirectional sync over a WebSocket, not a one-shot import/
export.

**Honesty note, matching the rest of this ecosystem's own documentation
convention:** this is a first real, working pass, not a finished product.
See [`docs/ROADMAP.md`](docs/ROADMAP.md) for exactly what's genuinely
implemented and verified end-to-end today vs. deliberately scoped out for
later. As of this pass, every real robot model this ecosystem supports has
real STL geometry and numerically-verified forward kinematics wired into
the 3D viewport (Parol6, Faze4, AR3, AR4, UR3e/5e/10e/16e/20, xArm6,
Lite 6, e.DO), plus a primitive-built "Generic" fallback for any model
without a dedicated mesh set.

---

## ✨ Visual Command Deck

The window has a persistent, game-console-inspired header using the official HYDRA-UMC icon and the deep navy/cyan language of HYDRA-UMC-UPDATER. It shows the product name, the live connection state and the version, and carries the global STOP button and the application menu (language, support bundle, keyboard shortcuts, About). Navigation to the panels is the left sidebar. It is not a simulated dashboard: every panel works on the real servers.

### 🛑 Global STOP

The **STOP** button is always at the top of the window, on every panel. One click, no confirmation: it calls `POST /api/stop-all` on every connected server and stops every robot, whoever reserved it. It shows the result: a green message when everything stopped, and a red one that stays until the next STOP when a robot did not stop, the stopped state could not be saved, or nothing confirmed the stop (**STOP NOT CONFIRMED**). If the server rate limits the call, the robots are stopped one by one. **F12** does the same from the keyboard (listed in **≡ > Keyboard shortcuts**); it is a bare function key, so it never presses a focused button and closes nothing.

### The Qt Quick interface

HYDRA-UMC SUITE has a single interface, written in Qt Quick (QML): a standalone `ApplicationWindow` (`assets/qml/Main.qml`) that `qt_suite.py` bridges to the unchanged `SuiteController`. It is the same pattern HYDRA-UMC-OS-REBUILDER, HYDRA-UMC-UPDATER, URTC-TESTER, URTC-FLASHER and HYDRA-UMC-EDITOR-URDF use, and the same shape as HYDRA-UMC-STUDIO: a navigation sidebar (a root menu plus the Industrial, URTC and HYDRA-UMC submenus, in `hydra_suite/nav_items.py`) and one content area that shows one of the 32 panels at a time. The 3D viewport and the previews are drawn by a dedicated `OffscreenRobotRenderer` (a separate `QOpenGLContext`, `QOffscreenSurface` and framebuffer, not Qt Quick's own `QQuickFramebufferObject`, which would force the whole interface off the Direct3D 11 backend Qt Quick uses by default on Windows onto OpenGL) with the same rendering code (`RobotGLRenderer`) and handed to QML as an image. The earlier classic window (a `QMainWindow` with dockable panels) was removed; everything it did lives in this interface, and `python main.py` starts it.

## 🏭 Features

- **🔍 Network discovery** - a concurrent subnet scan (`GET /api/hydra-info`)
  and real mDNS/Bonjour (`_hydra._tcp`, the same service `server.ts`
  publishes and HYDRA-UMC-IOS-CONTROL already queries) run together for
  real HYDRA-UMC SERVER instances, deduplicated by host:port, plus manual
  add-by-address for anything neither can reach (a different subnet, a
  VPN tunnel, multicast blocked by the network).
- **🐝 Swarm connections** - connect to as many HYDRA-UMC servers
  simultaneously as you want, each with its own live WebSocket sync; pick
  which one is "active" for the other panels.
- **📊 Overview** - per-controller robot roster: model, role, online
  status, speed/acceleration, at a glance.
- **🦾 Robot control** - a slider per joint inside the range of the model, speed/acceleration sliders, play / pause / stop of the recorded trajectory, the tool (with a confirmation), the valves and the pumps, all writing back live as atomic commands.
- **🔐 Reservations, safety limits and Live / Sim** - the Robot Control panel has an access bar: reserve or release the selected robot for this program (renewed while kept), see who holds the others and, as an administrator, take one over. Every reservation, release, jog arming and command carries the controller id this program chose when it started, and a refusal (another account, the same account elsewhere, a missing controller id, a jog that is not armed) reaches the screen with its own sentence. The size of a jog and the hottest heated-bed target are read from the server (`GET /api/safety-limits`) and checked before anything is sent; an administrator edits them by model in the **Safety limits** panel, together with the optional arming of the jog (off by default) and the mandatory controller id. Each robot has a **Live / Sim** switch (Live by default): in Sim nothing that moves the robot or switches something on leaves this program, while STOP always does. The joint sliders follow the range of the model, a Work with points outside it is refused with their list, a Work whose points the arm cannot reach is refused with those points and can be loaded scaled about the base of the robot, and switching the bed heater on asks first. Writes are conditional: each one carries the revision of the robot this program last saw (`If-Match`), and when someone else changed the robot in between the server answers 412, nothing is applied, the robot is read again and a notice says so (Standard checks reservations, the table and the one-off commands; Strict checks everything but STOP; Off checks nothing; the choice is under the list of reservations; STOP is never checked). The XY table jog is one atomic `table` command, the server pushes the reservations over the WebSocket so the panel stops polling while they arrive, and administrators read the append-only audit record, with its SHA-256 chain verified twice (by the server and here), under **Ecosystem > Audit record**. Administrators also create, change and delete the accounts of the server (administrator or operator) under **Ecosystem > Users**.
- **🧊 Real 3D viewport** - OpenGL 3.3, real STL meshes, real forward
  kinematics for all 24 real robot models (numerically verified against
  HYDRA-UMC STUDIO's own TypeScript implementation, bit-for-bit identical
  results) plus a primitive-built "Generic" fallback - not a stylized
  placeholder for any of them.
- **📍 Trajectory points** - record the selected robot's live pose, jog
  back to any recorded point on demand.
- **🧭 One sidebar, one content area** - the panels are reached from the left navigation (root menu plus the Industrial, URTC and HYDRA-UMC submenus), one at a time, grouped like HYDRA-UMC-STUDIO's sidebar. The window starts maximized with its native title bar, and **F11** toggles real full screen.
- **💾 Remembered servers and support bundle** - *Remember* is ticked by default when you add a server (untick it to keep nothing): its address, nickname and user name go to the configuration file and its password to the secure store of the operating system (Windows Credential Manager, macOS Keychain, the Secret Service of the Linux desktop) through `keyring`, never to the file; without a secure store the password is asked again. The application menu exports a zip for support with the versions, the server list and the client log, without passwords, user names or tokens.
- **🌐 8 languages** - English, Español, Italiano, Français, Deutsch, 简体中文,
  日本語, Português
  (same `language/*.lng` convention as URTC-FLASHER/URTC-TESTER), switch
  from the Language menu (takes effect after a restart).
- **📷 Cameras** - real per-controller camera roster (which cameras
  exist, their type, connected state, and a real USB/IP (RTSP) Source
  Type toggle with generic per-brand host/port/path/credential fields)
  synced with the real server the same way every other panel here is,
  plus real live video: the metadata is real end to end and each
  camera card renders the real MJPEG stream itself (HYDRA-UMC-
  VISION-STREAMER's own `stream serve`, proxied through HYDRA-UMC-
  SERVER's `GET /api/camera/:id/stream`) via a real JPEG SOI/EOI
  marker-scanning client (the same real approach HYDRA-UMC-ANDROID-
  CONTROL's own `MjpegStreamParser.kt` uses), verified against real USB
  and IP hardware.
- **🛠️ Tool-attachment config, all 11 of 11 panels** - CNC, Laser,
  Heated Bed, Vacuum Table, ATC (Automatic Tool Changer), XY Table,
  Rack Manager, Pick & Place, Kinematic Brain Stage, Flasher, and
  Tester - real feature parity with every one of HYDRA-UMC STUDIO's own
  tool-specific screens, each a faithful port (including the real,
  sometimes-quirky behavior STUDIO's own source has, reproduced on
  purpose rather than "fixed" here) with its own real headless test
  coverage. CNC/Laser/Heated Bed/Vacuum Table share one
  `moduleConfigComponent` implementation (STUDIO's own `CNC.tsx`/`Laser.tsx`
  are identical components apart from the module key); the other 7 each
  needed their own real, purpose-built panel. Heated beds and vacuum tables use STL in `render/module_rig.py`. PnP, CNC and laser use `render/pnp_rig.py`: 7 articulated meshes and 160 individual parts per independent machine directory. `OffscreenRobotRenderer` renders each assembly. See [machine assets](docs/MACHINE_ASSETS.md).

---

### 🧩 Selectable vacuum tables

Choose one of six real STL models in Vacuum Table: 160 × 120, 230 × 210, 230 × 250, 232 × 217, 240 × 240 or 250 × 250 mm. Base thickness is 15 mm; total height with alignment walls is 16.2 mm. Width and length are editable in 5 mm steps (10–5000 mm). The footprint is scaled; thickness stays unchanged. Selecting a preset restores its original dimensions. Custom sizes synchronize through SERVER; scaled holes/channels are a visual layout, not a regenerated manufacturing STL. Selection preserves placement, pump and valve state; reset selects 160 × 120 mm and switches pump and valve off. Legacy/unknown model IDs display the first model. STUDIO and both SUITE interfaces use the same catalog and modelId in robot settings.

[Model guide, configuration and regeneration](docs/VACUUM_TABLE_MODELS.md).

### 🔥 Heated bed model

Four STL presets: 100×100, 200×100, 200×200 and 255×255 mm, all 5 mm thick. Width/length adjust in 5 mm steps (25–5000 mm); selecting a preset restores its dimensions without changing heating. Visual model only, not an electrical or manufacturing design.

[Heated bed model — STL / OpenSCAD](docs/HEATED_BED_MODELS.md).

### 🗄️ Configurable STL racks

STL rack: width and depth 40–1000 mm in 1 mm steps; 1–24 plates at a fixed 10 mm pitch. Dimensions are visual settings, not robot calibration.

[Configurable STL racks — STL / OpenSCAD](docs/RACK_MODELS.md).

### 🛠️ Independent machine models

Independent STL copies for JuanenPnP, JuanenCNC and JuanenLaser; LumenPnP stays original. Edit each model in its own folder. CAD dimensions are used; legacy size settings do not stretch the model.

[Independent machine models — STL](docs/MACHINE_ASSETS.md).


These original JuanenPNP / HYDRA-UMC assets and their SCAD sources use GPL-3.0; they are not Opulo machine CAD.

## 📸 Photos

No screenshots yet - not yet captured for documentation. Launch it (see
below) to see the real thing rather than trust a stale image here later.

---

## 📂 Repository Structure

```text
HYDRA-UMC-SUITE/
├── docs/VACUUM_TABLE_MODELS.md
├── docs/HEATED_BED_MODELS.md
├── docs/RACK_MODELS.md
├── docs/MACHINE_ASSETS.md
├── assets/meshes/{juanenpnp,juanencnc,juanenlaser}/  # STL + ATTRIBUTION + VARIANT.md
├── tests/verify_machine_assets.py
├── assets/meshes/racks/default/        # Rack.scad + base/wall/guide/assembly STL
├── hydra_suite/racks.py
├── tests/verify_rack_geometry.py
├── assets/meshes/heatedbeds/default/  # catalog.json + HeatedBed.scad + 4 STL
├── hydra_suite/heated_beds.py
├── tests/verify_heated_beds.py
├── assets/meshes/vacuum-tables/default/  # catalog.json + 6 STL + 6 SCAD
├── hydra_suite/vacuum_tables.py
├── tests/verify_vacuum_tables.py
├── tests/verify_stop_all.py
├── tests/verify_hostile_server_answers.py
├── main.py                        # Entry point - starts the Qt Quick interface (maximized, 1280x720 min; F11 toggles real full screen)
├── qt_suite.py                     # Qt Quick front end - bridges the unchanged SuiteController to QML (all 32 panels)
├── verify_qt_suite_shell.py        # Real, hardware/network-free Qt Quick shell check - deliberately kept outside tests/ (same reason as URTC-TESTER/URTC-FLASHER's own verify_qt_*.py), run with `QT_QPA_PLATFORM=offscreen python verify_qt_suite_shell.py`
├── requirements.txt
├── hydra-umc.project.json         # Ecosystem manifest - version/family/parent, the source dashboard/updater/OS-REBUILDER read
├── bump_version.py                # Odometer-style version bump (run only by the explicit `bump` command)
├── bump_manifest_version.py       # Syncs hydra-umc.project.json's version to the native one (generic, copied verbatim across the ecosystem)
├── build-test.bat / build-test.sh # activates .venv and runs tools/build_test.py (the real test suite), non-mutating - never bumps the version or touches CHANGELOG.md
├── run.bat / run.sh               # Launches main.py through the venv
├── HYDRA-UMC_SUITE.spec           # PyInstaller spec (see build_exe.bat/.sh below)
├── build_exe.bat                  # One-shot Windows build -> dist/HYDRA-UMC_SUITE.exe
├── build_exe.sh                   # One-shot Linux build -> dist/HYDRA-UMC_SUITE
├── CHANGELOG.md / CODE_OF_CONDUCT.md / CONTRIBUTING.md / SECURITY.md / SUPPORT.md / LICENSE / LICENSE.md
├── README.md                      # this file
├── README_spa.md / README_fra.md / README_ita.md / README_deu.md / README_zho.md / README_jpn.md / README_por.md  <- translations
├── .github/                        # CI workflow, issue templates, PR template (generic, ecosystem-shared)
├── hydra_suite/
│   ├── models.py                   # HydraState/ControllerView/RobotView/CameraView - thin, mutation-friendly views over the real settings.json shape
│   ├── app.py                      # SuiteController - owns the swarm of connections, "active" selection, every panel talks to this
│   ├── i18n.py                     # 8-language KEY=Value loader (language/*.lng)
│   ├── can_ota.py                  # Shared CAN-OTA/SPI-OTA transport (real port of STUDIO's own canOta.ts) - used by Flasher and Tester
│   ├── logging_handler.py          # Routes Python logging into the Logs panel
│   ├── diagnostics.py              # Support bundle (zip with versions, servers and the log, credentials left out)
│   ├── net/
│   │   ├── discovery.py             # Concurrent subnet scan + real mDNS (_hydra._tcp) against GET /api/hydra-info, deduplicated
│   │   └── client.py                # Per-server REST + WebSocket connection, live bidirectional sync, login, admin/discovery/PTZ endpoints
│   ├── render/
│   │   ├── kinematics.py            # Forward kinematics (ported from HYDRA-UMC-STUDIO's own urKinematicsShared.ts)
│   │   ├── generic_rig.py           # Primitive-built fallback rig for any model with no dedicated mesh set
│   │   ├── module_rig.py            # Tool-attachment module geometry (CNC/Laser/Heated Bed/Vacuum Table)
│   │   ├── pnp_rig.py               # Real Cartesian-gantry chain for the LumenPnP/JuanenPnP mesh rig
│   │   ├── mesh.py                  # STL loading (numpy-stl)
│   │   └── viewport.py              # RobotGLRenderer (real GLSL shader pipeline, orbit camera) + OffscreenRobotRenderer, which draws the 3D viewport and the previews of the Qt Quick interface
│   ├── access.py                   # Controller id, reservations, safety limits read from the server, Live / Sim - no Qt, no network
│   ├── reach.py                    # Where the tool of each model can be, inverse kinematics and scaling of Works - no Qt, no network
│   ├── credentials.py              # Remembered servers: the configuration file and the secure store of the operating system (keyring)
│   ├── joint_limits.py             # Range of each joint of the models that publish one
│   ├── nav_items.py                # The navigation: root menu and the Industrial / URTC / HYDRA-UMC submenus
│   └── panel_logic/                # What the panels need that does not depend on a window: tiers, defaults, MJPEG parsing, supervisor charts
├── assets/
│   ├── qml/Main.qml                 # The Qt Quick interface (all 32 panels)
│   └── meshes/                      # Real STL meshes, one folder per robot/module, copied from HYDRA-UMC-STUDIO's own public/models/ (each with its own ATTRIBUTION.txt)
├── language/                        # english/spanish/french/german/italian/japanese/chinese/portuguese .lng files
├── docs/
│   └── ROADMAP.md                   # Honest real-vs-not-yet scope statement
├── tools/
│   ├── build_test.py                # Non-versioning build/compile check (generic, ecosystem-shared) - also runs run_offline_verifiers.py below when present
│   ├── ci_validate.py               # Manifest/CHANGELOG/docs validation used by CI (generic, ecosystem-shared)
│   └── run_offline_verifiers.py     # `python tools/run_offline_verifiers.py` - every tests/verify_*.py under a headless Qt platform (QT_QPA_PLATFORM=offscreen), real regression coverage for each panel's own Qt/backend wiring
├── tests/                           # Real headless test suite (QApplication, no display needed) - one verify_*.py per panel/subsystem, plus kinematics ports and manual smoke tests that need a real running STUDIO server
├── installer/                       # Platform packaging notes/assets
└── .vscode/                         # Python interpreter path, launch configs, recommended extensions
```

---

## 🚀 Getting Started

### Requirements
- Python 3.12+ (the CI runs 3.12; also run locally on 3.14)
- A running [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) server to connect to

### Installation

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # Linux

pip install -r requirements.txt
```

### Running

```bash
python main.py
```

Starts maximized at a 1280x720 minimum (per this app's own design spec)
- press **F11** to toggle between fullscreen and the maximized
window at any time, so it never actually traps you without an escape
hatch. Use the **Servers** panel to scan your network or add a HYDRA-UMC
SERVER by address.

Press **F12** at any time to send the global STOP (the **STOP** button in the top bar does the same).

---

## 🛠️ Technology Stack

- **UI framework:** PySide6 (Qt6) with Qt Quick (QML) - one interface, no custom docking framework reinvented
- **3D rendering:** PyOpenGL (core-profile GLSL shaders) + numpy-stl
- **Networking:** `httpx` (REST) + `websockets` (live sync), integrated
  with Qt's own event loop via `qasync` - no separate worker thread
- **Math:** NumPy (4x4 homogeneous transforms for forward kinematics)

---

## 📦 Building a standalone executable

Two paths, same result (`dist/HYDRA-UMC_SUITE.exe` on Windows,
`dist/HYDRA-UMC_SUITE` on Linux) - no Python installation needed to run
the output either way.

**Automated (recommended):**

```bash
build_exe.bat    # Windows
./build_exe.sh   # Linux
```

Each script creates/reuses `.venv`, installs `requirements.txt` +
PyInstaller into it, cleans any previous `build/`/`dist/`, compiles with
PyInstaller (bundling `assets/` and only the 4 Qt plugin subfolders this
app actually uses - `platforms`/`styles`/`imageformats`/`iconengines`,
not the whole PySide6 package, which is what keeps the result in the tens
of MB instead of hundreds), and copies `README.md`/`LICENSE`/`docs/` and
the editable `language/*.lng` files next to the executable rather than
freezing them inside it.

**Manual equivalent**, if you want to see/control every step yourself
(same commands the scripts above run):

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate      # Linux

pip install -r requirements.txt
pip install pyinstaller

python -m PyInstaller --onefile --windowed --noconfirm --name "HYDRA-UMC_SUITE" ^
    --add-data "assets;assets" ^
    --add-data "<PySide6 install dir>\plugins\platforms;PySide6\plugins\platforms" ^
    --add-data "<PySide6 install dir>\plugins\styles;PySide6\plugins\styles" ^
    --add-data "<PySide6 install dir>\plugins\imageformats;PySide6\plugins\imageformats" ^
    --add-data "<PySide6 install dir>\plugins\iconengines;PySide6\plugins\iconengines" ^
    --hidden-import qasync --hidden-import websockets ^
    --hidden-import PySide6.QtOpenGL --hidden-import PySide6.QtOpenGLWidgets ^
    --hidden-import OpenGL.platform.win32 ^
    main.py

# then copy README.md, LICENSE, docs/, and language/ next to dist/HYDRA-UMC_SUITE.exe
```

On Linux (see `build_exe.sh` for the exact, tested command), use `:`
instead of `;` as the `--add-data` separator, drop the
`OpenGL.platform.win32` hidden-import (Windows-only), drop `--windowed`,
and note the plugin path nests one level deeper there
(`<PySide6 dir>/Qt/plugins/platforms` vs. Windows's flat
`<PySide6 dir>\plugins\platforms`) - a packaging detail of the wheel
itself, not something either script chose. `HYDRA-UMC_SUITE.spec` at the
repo root is PyInstaller's own generated spec file from the last build -
safe to delete and regenerate, not hand-maintained.

---

## 🔢 Versioning

`hydra_suite/__version__` (shown in **Help > About**) follows an
odometer-style `MAJOR.MINOR.PATCH` scheme with a base-10 carry rule: patch goes up by 1 on every bump; once it would pass 9, it resets to 0 and
minor goes up by 1 instead (e.g. `0.1.9` -> `0.2.0`). The bump itself is the explicit command `python tools/hydra_project_tool.py bump`, which runs `bump_version.py`; building with `build_exe.bat`/`build_exe.sh` never changes the version.exe`/binary always carries a version number strictly newer
than the last one actually shipped. See [`CHANGELOG.md`](CHANGELOG.md) for
what changed at each point.

---

## 🔗 Related Projects

This project is part of the HYDRA-UMC robotics ecosystem by the same author (JuanenRac / Electro Hobby 3D). Worth knowing about, since a request might actually be about one of these rather than this repository.

**Parent Project**
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — the real headless backend (REST/WebSocket) every control client actually talks to; this suite is a real client of its own API, network-discovering it over mDNS.

**Sibling Projects** — also talk to HYDRA-UMC-SERVER's own API, each their own client
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — web control dashboard with real-time multi-robot 3D visualization.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android control app with biometric login and a paired Wear OS companion.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS control app (Flutter) with real-time WebSocket sync.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native touch UI for the onboard 7" DSI touchscreen, embedded on the CM5 itself.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — coordination boundary for AGV/AMR fleets via a VDA 5050 MQTT publisher (tested against an emulated fleet only).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — high-level CNC-cell coordinator with GRBL status/control-byte access (tested against an emulator only).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — coordination boundary for legged/humanoid droids, with a Boston Dynamics Spot command sender (tested against an emulator only).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — laser-cell coordinator reading 3 key/enclosure/interlock GPIO signals (tested against a fake chip only; it cannot arm or fire a laser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — safe high-level board-flow coordinator for OpenPnP pick-and-place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — safe coordination boundary for Moonraker/Klipper 3D printers, with real gated job commands.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinator with a lazily imported rclpy ROS 2 transport (not yet run against a ROS 2 installation).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — coordination boundary for camera-equipped UAVs, with a MAVLink command sender (tested against an emulator only).

**Directly Related**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — hardware-in-the-loop router with a software collision interlock between simulation and real hardware (tested without real hardware); lets this suite drive the digital twin as if it were real hardware, swapping a live HYDRA-UMC controller for a hardware-in-the-loop bridge without changing anything else in the workflow.
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — integration hub with a real gRPC/Protobuf health-report contract and mission state machine; the swarm command center this suite ultimately answers to, coordinating fleets of HYDRA-UMC controllers at a level above what a single desktop session can reach.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — fleet CLI with a real, stable exit-code contract, a genuine live client of HYDRA-UMC-SERVER's own API; offers the same DevOps feature set as this desktop suite from the command line, for scripting and headless environments.

**Also Part of the Ecosystem**

*Core Hardware & Platform*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — the robot-arm motherboard design: CM5 host + dual-core STM32H745, meant to orchestrate up to 8 tool arms over CAN-OTA/SPI-OTA (firmware at an early stage; no populated board yet).
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproducible Raspberry Pi OS product layer for the CM5: read-only agent, validated config/profiles, WiFi first-contact provisioning.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — the shared JSON-Schema contract and software job-gate boundary every bridge validates its commands against (not a certified safety function).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — declarative adapter-manifest registry and validator for external-machine connectors; extends the SDK's own contract idea to external machines without replacing the industrial-gateway projects.

*Core Backend & Clients*
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — desktop graphical URDF creator/editor that pushes finished models into STUDIO's own catalog.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — desktop STL model editor for this app's own `assets/meshes/` library (and STUDIO's own mirror of it) - transform/replace/remove/add real parts, never permanently deleting anything.

*URTC Tool Platform*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware for the physical Universal Robot Tool Controller PCB, 25+ tool profiles over CAN bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — desktop GUI flashing tool for URTC boards, CAN-OTA plus full-chip SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — desktop live CAN-bus diagnostic tool for URTC boards, one panel per tool profile.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browser-based alternative to URTC-TESTER via the Web Serial API, no local install needed.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — gateway in front of the URTC CAN bus: an allowed list of identifiers, a rate limit and a session key; software tested on a computer, not yet on a real bus.

*Vision AI Node (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — integration hub for the Hailo-8 vision pipeline, with a real per-stage hardware-readiness check.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — real compiled-model registry with Hailo-architecture/checksum safe-load verification.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — real GStreamer pipeline + MediaMTX config generator with a real HailoRT integration boundary.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — Position-Based Visual Servoing correction law with authorisation gated on the zone state; no camera pose estimation yet.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — v0 zone-breach, calibration-freshness and E-STOP-request logic that takes object positions from a file; no detector feeds it and no physical E-STOP is wired to it yet.

*Cognitive AI Node (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — integration hub for the Hailo-10 cognitive pipeline (LLM/VLA/voice orchestration).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — real action-token encoding/decoding and trajectory generation for a Vision-Language-Action model.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — real voice front-end (VAD + intent parser) with a bounded, confirmation-gated Watch relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — real rule-based task decomposition and semantic error recovery over MCU error codes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — real stdlib-only TF-IDF document search over this ecosystem's own Markdown docs.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — local, policy-gated AI maintenance technician for the ecosystem itself - observes, diagnoses and proposes fixes; the two highest risk levels are deliberately not implemented yet.

*Orchestration & Swarm*
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — real priority-based job queue with deduplication, over a real HTTP API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — real gRPC-based fleet health watchdog with retry/backoff and identity-mismatch detection.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — real RRT-based 3D path planner with real obstacle/workspace collision validation.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — real CRDT LWW-Element-Map state sync, property-tested for multi-cell convergence.

*Digital Twin & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — integration hub for the digital-twin engine, with a real version-compatibility sync contract.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — real forward kinematics and joint-limit validation over a real URDF subset.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — real procedural 2D scene generator with YOLO/COCO annotation export.

*Data & Analytics*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — real sqlite3-backed time-series store with a real ingest/query HTTP API.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — real FFT + statistical baseline anomaly detector with drift monitoring.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — real OEE/availability calculation over DATALAKE history, with reproducible CSV export.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — real CAN/WebSocket ingestion pipeline into DATALAKE, with sequence deduplication.

*Industrial Gateway*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — integration hub relaying to industrial protocols, with a real command allowlist/backpressure layer.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — real OPC-UA address space, verified with a real binary-protocol client session.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — real MQTT broker with optional per-client authentication and topic ACLs.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — real MTConnect `/probe` and `/current` XML endpoints with degraded-mode output.

*Complementary Tools & Ecosystem Operations*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — Smart Summaries and Anomaly Highlighting panels over DATALAKE/ANOMALY-DETECTOR, with an honest statistical fallback.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS companion app with haptic alert patterns and a paired-phone voice relay (not yet run on a physical watch).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware for a board-mounting rack with real tool-ID decoding and Smart Idle pre-heating logic.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus a real Python vision companion for a thermal/RGB inspection tool head.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — administrative desktop tool that discovers, clones and updates every repo in this ecosystem.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — Windows/Linux desktop tool that builds a ready-to-flash CM5 image pre-loaded with the ecosystem's most current versions, with Raspberry-Pi-Imager-style first-boot Wi-Fi/user/SSH configuration.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — maintenance-incident coordinator: a low-privilege edge role collects a sanitized inventory/health snapshot, a control-plane role renders it read-only and asks an AI provider to suggest a diagnosis - never applies a patch or deploys anything.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — reproducible development host (Raspberry Pi 5 / CM5) that stores the ecosystem's source and runs bounded build/test tasks under a durable queue; a dedicated dev role, explicitly not an operational CM5.

---

## 📚 Documentation & Community

- **[docs/ROADMAP.md](docs/ROADMAP.md)** — what's real and verified end-to-end today versus what's deliberately still out of scope.
- **[installer/README.md](installer/README.md)** — building the Windows `.exe` installer and the Linux `.deb` package.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — tech stack and coding guidelines for a pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — the standards of behavior expected in this community.
- **[SECURITY.md](SECURITY.md)** — how to report a vulnerability, and this app's own real security focus areas.
- **[SUPPORT.md](SUPPORT.md)** — where to ask questions and report bugs.
- **[LICENSE.md](LICENSE.md)** — this project's own license, plus the separate license each `assets/meshes/` folder is redistributed under.

## 👤 AUTHOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENSE

HYDRA-UMC SUITE is (c) 2026 JuanenRac (Electro Hobby 3D). This notice must be included in any distributions of this project or derivative works.

The source code of this application is available under the **GNU General Public License v3.0 (GPL-3.0)**. Full text at https://www.gnu.org/licenses/gpl-3.0.html.

**This documentation** (this README and its own translations - `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`, `README_zho.md`, `README_jpn.md`, `README_por.md`) is available under **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. Full text at https://creativecommons.org/licenses/by-sa/4.0/.

**Third-party mesh assets:** every folder under `assets/meshes/` is copied verbatim from that robot's own official manufacturer repository - NOT covered by the GPL-3.0 above. Each has its own `ATTRIBUTION.txt` with the exact source/license reference; the table below summarizes them.

| Manufacturer | Models | License |
|---|---|---|
| Source Robotics | Parol6 | GPL-3.0 |
| Source Robotics | Faze4 | MIT |
| Annin Robotics | AR3, AR4 | MIT |
| Universal Robots | UR3e, UR5e, UR10e, UR16e, UR20 | BSD-3-Clause |
| UFACTORY | xArm6, Lite 6 | BSD-3-Clause |
| Comau | e.DO | BSD-3-Clause |
| Kinova | Gen3 Lite | BSD-3-Clause |
| FANUC | M-710iC | BSD-3-Clause |
| The Robot Studio | SO-ARM100 | Apache-2.0 |
| Kinova | Gen2 (j2s6s200) | BSD-3-Clause |
| AgileX | PiPER | Apache-2.0 |
| Unitree | Z1 | BSD-3-Clause |
| Trossen Robotics | ViperX 300, WidowX 250 | BSD-3-Clause |
| Koch / Low-Cost Robot Arm | Koch v1.1 | Apache-2.0 |
| Universal Robots (classic) | UR3, UR5, UR10 | BSD-3-Clause |

This project is the desktop swarm-control counterpart to [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) - see that project's own repository for its own separate license, which this repository's own license doesn't extend to, and vice versa. It also ultimately controls [HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) hardware/firmware and ([relayed through it](https://github.com/JuanenRac/HYDRA-UMC/blob/main/docs/architecture.md)) [URTC](https://github.com/JuanenRac/URTC) tool heads - both separate projects with their own separate licenses.

If you build on this project, keep the licensing split in mind: code changes should stay GPL-3.0, and every robot's own mesh assets should stay under their own original license terms (see the table above) - each with attribution back to this project and its author.
