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

<p align="left">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.12-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="PySide6">
  <img src="https://img.shields.io/badge/Graphics-OpenGL-5586A4.svg" alt="OpenGL">
</p>


---

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

The desktop now has a persistent, game-console-inspired command deck using the official HYDRA-UMC icon and the deep navy/cyan language of HYDRA-UMC-UPDATER. Its Dashboard, Robot Control, Cameras, Trajectory and Logs controls raise the corresponding real dockable panels; its right side shows live connection state, selected server target and UTC time. It is a visual layer over existing Suite functions, not a simulated dashboard.

## 🏭 Features

- **🔍 Network discovery** - a concurrent subnet scan (`GET /api/hydra-info`)
  and real mDNS/Bonjour (`_hydra._tcp`, the same service `server.ts`
  publishes and HYDRA-UMC-IOS-CONTROL already queries) run together for
  real HYDRA-UMC STUDIO servers, deduplicated by host:port, plus manual
  add-by-address for anything neither can reach (a different subnet, a
  VPN tunnel, multicast blocked by the network).
- **🐝 Swarm connections** - connect to as many HYDRA-UMC servers
  simultaneously as you want, each with its own live WebSocket sync; pick
  which one is "active" for the other panels.
- **📊 Overview** - per-controller robot roster: model, role, online
  status, speed/acceleration, at a glance.
- **🦾 Robot control** - rotary knob + slider per joint (the desktop
  counterpart to HYDRA-UMC STUDIO's own `RotaryKnob`+`FuturisticSlider`
  jog pair), speed/acceleration sliders, all writing back live.
- **🧊 Real 3D viewport** - OpenGL 3.3, real STL meshes, real forward
  kinematics for all 24 real robot models (numerically verified against
  HYDRA-UMC STUDIO's own TypeScript implementation, bit-for-bit identical
  results) plus a primitive-built "Generic" fallback - not a stylized
  placeholder for any of them.
- **📍 Trajectory points** - record the selected robot's live pose, jog
  back to any recorded point on demand.
- **🪟 Photoshop-style dockable workspace** - every panel is a real
  `QDockWidget`: drag to float free, drag back to dock or merge into a
  tab group, split the workspace, close, and re-show from the View menu.
  Floating a panel makes it a genuine independent top-level window, so
  dragging it onto a second (or third) physical monitor and leaving it
  there works out of the box - Qt/the OS window manager places it like
  any other window, no extra "multi-monitor mode" needed.
- **🌐 7 languages** - English, Español, Italiano, Français, Deutsch, 简体中文,
  日本語
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
  `ModuleConfigPanel` implementation (STUDIO's own `CNC.tsx`/`Laser.tsx`
  are identical components apart from the module key); the other 7 each
  needed their own real, purpose-built panel. The one remaining gap
  versus STUDIO is the live 3D preview most of these panels have there -
  `render/viewport.py` has no attached-module-geometry support yet.

---

## 📸 Photos

No screenshots yet - not yet captured for documentation. Launch it (see
below) to see the real thing rather than trust a stale image here later.

---

## 📂 Repository Structure

```text
HYDRA-UMC-SUITE/
├── main.py                        # Entry point - fullscreen 1920x1080 min, F11 toggles fullscreen/windowed
├── requirements.txt
├── HYDRA-UMC_SUITE.spec           # PyInstaller spec (see build_exe.bat/.sh below)
├── build_exe.bat                  # One-shot Windows build -> dist/HYDRA-UMC_SUITE.exe
├── build_exe.sh                   # One-shot Linux build -> dist/HYDRA-UMC_SUITE
├── README.md                      # this file
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md / README_zho.md / README_jpn.md  <- translations
├── hydra_suite/
│   ├── models.py                   # HydraState/ControllerView/RobotView - thin, mutation-friendly views over the real settings.json shape
│   ├── app.py                      # SuiteController - owns the swarm of connections, "active" selection, every panel talks to this
│   ├── i18n.py                     # 7-language KEY=Value loader (language/*.lng)
│   ├── net/
│   │   ├── discovery.py             # Concurrent subnet scan + real mDNS (_hydra._tcp) against GET /api/hydra-info, deduplicated
│   │   └── client.py                # Per-server REST + WebSocket connection, live bidirectional sync, login
│   ├── render/
│   │   ├── kinematics.py            # Forward kinematics (ported from HYDRA-UMC-STUDIO's own urKinematicsShared.ts)
│   │   ├── generic_rig.py           # Primitive-built fallback rig for any model with no dedicated mesh set
│   │   ├── mesh.py                  # STL loading (numpy-stl)
│   │   └── viewport.py              # QOpenGLWidget - real GLSL shader pipeline, orbit camera
│   └── ui/
│       ├── main_window.py           # QMainWindow + QDockWidget workspace
│       ├── theme.py                  # Loads assets/qss/industrial_dark.qss
│       ├── widgets/rotary_knob.py    # Custom-painted rotary knob (desktop counterpart to RotaryKnob.tsx)
│       └── panels/                   # server_browser.py, overview.py, robot_control.py, viewport_panel.py, trajectory_panel.py, cameras_panel.py
├── assets/
│   ├── qss/industrial_dark.qss     # The futuristic-industrial Qt stylesheet
│   └── meshes/                      # Real STL meshes, one folder per robot (24 models), copied from HYDRA-UMC-STUDIO's own public/models/<robot>/ (each with its own ATTRIBUTION.txt)
├── language/                        # english/spanish/italian/french/german .lng files
├── docs/
│   └── ROADMAP.md                   # Honest real-vs-not-yet scope statement
├── tests/                           # Manual integration smoke tests (require a real running HYDRA-UMC STUDIO server - not a mocked unit suite) + kinematics verification scripts
└── .vscode/                         # Python interpreter path, launch configs, recommended extensions
```

---

## 🚀 Getting Started

### Requirements
- Python 3.12+ (developed/tested against 3.14)
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

Starts fullscreen at a 1920x1080 minimum (per this app's own design spec)
- press **F11** to toggle between fullscreen and a normal maximized
window at any time, so it never actually traps you without an escape
hatch. Use the **Servers** panel to scan your network or add a HYDRA-UMC
STUDIO server by address.

---

## 🛠️ Technology Stack

- **UI framework:** PySide6 (Qt6) - native dockable panels, no custom
  docking framework reinvented
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
odometer-style `MAJOR.MINOR.PATCH` scheme with a base-10 carry rule: patch
goes up by 1 on every real build; once it would pass 9, it resets to 0 and
minor goes up by 1 instead (e.g. `0.1.9` -> `0.2.0`). "A real build" means
a run of `build_exe.bat`/`build_exe.sh` - **not** every plain
`python main.py` run. The bump itself is handled automatically by
`bump_version.py` (called by both build scripts, before PyInstaller runs)
so a packaged `.exe`/binary always carries a version number strictly newer
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
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — coordination boundary for AGV/AMR fleets via a real VDA 5050 MQTT publisher.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — high-level CNC-cell coordinator with real GRBL status/control-byte access.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — coordination boundary for legged/humanoid droids, with a real Boston Dynamics Spot command sender.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — laser-cell safety coordinator reading 3 real key/enclosure/interlock GPIO safeguards.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — safe high-level board-flow coordinator for OpenPnP pick-and-place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — safe coordination boundary for Moonraker/Klipper 3D printers, with real gated job commands.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — safety coordinator with a real, lazily-imported rclpy ROS 2 transport.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — coordination boundary for camera-equipped UAVs, with a real MAVLink command sender.

**Directly Related**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — real hardware-in-the-loop safety interlock routing commands between simulation and real hardware; lets this suite drive the digital twin as if it were real hardware, swapping a live HYDRA-UMC controller for a hardware-in-the-loop bridge without changing anything else in the workflow.
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — integration hub with a real gRPC/Protobuf health-report contract and mission state machine; the swarm command center this suite ultimately answers to, coordinating fleets of HYDRA-UMC controllers at a level above what a single desktop session can reach.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — fleet CLI with a real, stable exit-code contract, a genuine live client of HYDRA-UMC-SERVER's own API; offers the same DevOps feature set as this desktop suite from the command line, for scripting and headless environments.

**Also Part of the Ecosystem**

*Core Hardware & Platform*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — the physical robot-arm motherboard: CM5 host + dual-core STM32H745, orchestrating up to 8 tool arms over CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproducible Raspberry Pi OS product layer for the CM5: read-only agent, validated config/profiles, WiFi first-contact provisioning.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — the shared JSON-Schema contract and safety-gate boundary every bridge validates its commands against.

*Core Backend & Clients*
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — desktop graphical URDF creator/editor that pushes finished models into STUDIO's own catalog.

*URTC Tool Platform*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware for the physical Universal Robot Tool Controller PCB, 25+ tool profiles over CAN bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — desktop GUI flashing tool for URTC boards, CAN-OTA plus full-chip SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — desktop live CAN-bus diagnostic tool for URTC boards, one panel per tool profile.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browser-based alternative to URTC-TESTER via the Web Serial API, no local install needed.

*Vision AI Node (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — integration hub for the Hailo-8 vision pipeline, with a real per-stage hardware-readiness check.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — real compiled-model registry with Hailo-architecture/checksum safe-load verification.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — real GStreamer pipeline + MediaMTX config generator with a real HailoRT integration boundary.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — real Position-Based Visual Servoing correction law, safety-gated on upstream zone state.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — real zone-breach checking and E-STOP requesting, with calibration-freshness enforcement.

*Cognitive AI Node (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — integration hub for the Hailo-10 cognitive pipeline (LLM/VLA/voice orchestration).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — real action-token encoding/decoding and trajectory generation for a Vision-Language-Action model.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — real voice front-end (VAD + intent parser) with a bounded, confirmation-gated Watch relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — real rule-based task decomposition and semantic error recovery over MCU error codes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — real stdlib-only TF-IDF document search over this ecosystem's own Markdown docs.

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
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS companion app with real haptic alerts and a paired-phone voice relay.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware for a board-mounting rack with real tool-ID decoding and Smart Idle pre-heating logic.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus a real Python vision companion for a thermal/RGB inspection tool head.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — administrative desktop tool that discovers, clones and updates every repo in this ecosystem.

---

## 👤 AUTHOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENSE

HYDRA-UMC SUITE is (c) 2026 JuanenRac (Electro Hobby 3D). This notice must be included in any distributions of this project or derivative works.

The source code of this application is available under the **GNU General Public License v3.0 (GPL-3.0)**. Full text at https://www.gnu.org/licenses/gpl-3.0.html.

**This documentation** (this README and its own translations - `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`, `README_zho.md`, `README_jpn.md`) is available under **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. Full text at https://creativecommons.org/licenses/by-sa/4.0/.

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
