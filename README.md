<p align="center">
  <img src="images/HYDRA_UMC_SUITE_BANNER.jpg" alt="HYDRA-UMC Suite Banner" width="100%">
</p>

# 🧰 HYDRA-UMC SUITE

### 🖥️ Multi-Controller Swarm Command Center for the HYDRA-UMC Platform

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
[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)'s own
browser UI does - see
[`HYDRA-UMC-STUDIO/docs/REMOTE_API.md`](https://github.com/JuanenRac/HYDRA-UMC-STUDIO/blob/main/docs/REMOTE_API.md)
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

## 🏭 Features

- **🔍 Network discovery** - concurrent subnet scan for real HYDRA-UMC
  STUDIO servers (`GET /api/hydra-info`), plus manual add-by-address for
  anything a scan can't reach (a different subnet, a VPN tunnel).
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
- **🌐 5 languages** - English, Español, Italiano, Français, Deutsch
  (same `language/*.lng` convention as URTC-FLASHER/URTC-TESTER), switch
  from the Language menu (takes effect after a restart).
- **📷 Cameras** - real per-controller camera roster (which cameras
  exist, their type, connected state) synced with the real server the
  same way every other panel here is - the video feed itself is a
  clearly-labeled placeholder, matching HYDRA-UMC-STUDIO's own
  CamerasView.tsx honesty boundary (no real camera hardware/stream
  exists anywhere in this ecosystem yet).

---

## 📸 Photos

No screenshots yet - this is a freshly-built application as of 15 August
2026, not yet captured for documentation. Launch it (see below) to see
the real thing rather than trust a stale image here later.

---

## 📂 Repository Structure

```text
HYDRA-UMC-SUITE/
├── main.py                      # Entry point - fullscreen 1920x1080 min, F11 toggles fullscreen/windowed
├── requirements.txt
├── hydra_suite/
│   ├── models.py                 # HydraState/ControllerView/RobotView - thin, mutation-friendly views over the real settings.json shape
│   ├── app.py                    # SuiteController - owns the swarm of connections, "active" selection, every panel talks to this
│   ├── net/
│   │   ├── discovery.py           # Concurrent subnet scan against GET /api/hydra-info
│   │   └── client.py              # Per-server REST + WebSocket connection, live bidirectional sync
│   ├── render/
│   │   ├── kinematics.py          # Forward kinematics (ported from HYDRA-UMC-STUDIO's own urKinematicsShared.ts)
│   │   ├── mesh.py                # STL loading (numpy-stl)
│   │   └── viewport.py            # QOpenGLWidget - real GLSL shader pipeline, orbit camera
│   └── ui/
│       ├── main_window.py         # QMainWindow + QDockWidget workspace
│       ├── theme.py                # Loads assets/qss/industrial_dark.qss
│       ├── widgets/rotary_knob.py  # Custom-painted rotary knob (desktop counterpart to RotaryKnob.tsx)
│       └── panels/                 # server_browser.py, overview.py, robot_control.py, viewport_panel.py, trajectory_panel.py
├── assets/
│   ├── qss/industrial_dark.qss   # The futuristic-industrial Qt stylesheet
│   └── meshes/                    # Real STL meshes, one folder per robot, copied from HYDRA-UMC-STUDIO's own public/models/<robot>/ (each with its own ATTRIBUTION.txt)
├── docs/
│   └── ROADMAP.md                 # Honest real-vs-not-yet scope statement
├── tests/                         # Manual integration smoke tests (require a real running HYDRA-UMC STUDIO server - not a mocked unit suite)
└── .vscode/                       # Python interpreter path, launch configs, recommended extensions
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

## 🔗 Related Projects

This project is part of a larger robotics ecosystem by the same author (JuanenRac / Electro Hobby 3D). Worth knowing about, since a request might actually be about one of these rather than this repository:

**HYDRA-UMC platform** — the multi-robot micro-factory cell
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — the motherboard itself: Raspberry Pi CM5 host + dual-core STM32H745 real-time co-processor, orchestrating up to 8 distributed robot arms over CAN-OTA/SPI-OTA. Own hardware + firmware, GPL-3.0/CERN-OHL-S v2/CC BY-SA 4.0.
- **[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — web-based control dashboard for HYDRA-UMC: multi-robot 3D visualization, kinematics/trajectory recording, CAN-OTA flashing and testing for the whole platform. React + Vite + Three.js.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — Android control app for HYDRA-UMC (Wi-Fi transport speaks this same REMOTE_API.md contract). Scaffolding stage.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS control app for HYDRA-UMC, same contract. Scaffolding stage.
- **HYDRA-UMC-SUITE** *(this repository)* — this project.

**URTC platform** — the tool head controller every HYDRA-UMC robot arm carries
- **[URTC](https://github.com/JuanenRac/URTC)** — Universal Robot Tool Controller: STM32F303-based CAN bus tool head controller, 25 fully-implemented tool profiles, CAN-OTA firmware update.
- **[URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)** — desktop CAN-OTA + full-chip SWD/JTAG flashing tool for URTC boards (Windows/Linux).
- **[URTC Tester](https://github.com/JuanenRac/URTC-TESTER)** — desktop live CAN-bus diagnostic tool for URTC boards, one panel per tool profile (Windows/Linux).
- **[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browser-based alternative to the 2 desktop tools above (Web Serial API + SLCAN), no local install needed.

---

## 👤 Author

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 youtube.com/@electrohobby3d

---

## 📜 License and Copyright Notices

HYDRA-UMC SUITE is (c) 2026 JuanenRac (Electro Hobby 3D). This notice must be included in any distributions of this project or derivative works.

The source code of this application is available under the **GNU General Public License v3.0 (GPL-3.0)**. Full text at https://www.gnu.org/licenses/gpl-3.0.html.

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
