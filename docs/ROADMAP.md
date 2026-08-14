# HYDRA-UMC SUITE - Roadmap / Honest Scope Statement

What's real today vs. deliberately left for a future pass, matching this
ecosystem's own established documentation convention of not overstating
what's implemented. Every item below is a genuine gap, not a hidden bug -
each one is a scoped, well-understood next step, not a redesign.

## ✅ Real and verified end-to-end (15 August 2026)

- **Network discovery** (`hydra_suite/net/discovery.py`) - concurrent
  subnet scan hitting `GET /api/hydra-info` on every candidate host,
  tested against a real running HYDRA-UMC STUDIO server.
- **Live connection** (`hydra_suite/net/client.py`) - REST read/write +
  WebSocket live sync, implementing
  [`HYDRA-UMC-STUDIO/docs/REMOTE_API.md`](https://github.com/JuanenRac/HYDRA-UMC-STUDIO/blob/main/docs/REMOTE_API.md)
  exactly. Verified: connects, receives real state (8 robots), pushes a
  joint change, receives the broadcast echo correctly suppressed.
- **Swarm support** (`hydra_suite/app.py`'s `SuiteController`) - holds an
  arbitrary number of simultaneous `HydraConnection`s, one per added
  server, with one "active" for the other panels to show.
- **3D viewport** (`hydra_suite/render/`) - real forward kinematics
  (`kinematics.py`, numerically verified to match HYDRA-UMC-STUDIO's own
  TypeScript FK bit-for-bit: both report 849.7401073213356mm for UR5e's
  fully-extended horizontal reach) driving real STL meshes (`mesh.py`,
  the exact same files as HYDRA-UMC-STUDIO's own `public/models/ur5e/`)
  through a real OpenGL 3.3 core-profile shader pipeline (`viewport.py`).
  Verified with actual GL context creation, shader compile/link, and
  multiple real paint passes at different joint poses on this machine's
  real GPU driver, not just unit-tested math.
- **Jog controls, Overview, Server Browser, local trajectory point
  recorder** - all read/write against the real live state of whichever
  server is active.
- **Photoshop-style dockable workspace** - real `QDockWidget`s (Qt's own
  mature docking system), not a custom-built one - float, dock, tab
  together, split, close, and re-show via the View menu all work because
  Qt itself already implements them correctly.

## 🚧 Deliberately out of scope this pass

- **3D geometry for the other 8 robot models** (Parol6, Faze4, AR3, AR4,
  UR3e, UR10e, UR16e, UR20) - only UR5e has real STL+kinematics data
  ported into this Python app (`hydra_suite/render/kinematics.py`'s own
  header explains why the UR family's shared-structure data is the
  cheapest to extend). Selecting a robot with an unsupported model shows
  an honest "not wired up yet" message in the viewport panel instead of
  silently rendering the wrong shape. Porting another model is: extract
  its chain/mesh-offset data from HYDRA-UMC-STUDIO's own
  `src/examples/<model>Kinematics.ts` (same numbers, already verified
  there), copy its STL set from `public/models/<model>/`, add it to
  `kinematics.py` and `viewport.py`'s link-file map - no new rendering
  engine work needed, the pipeline is already model-agnostic.
- **Trajectory file format parity with HYDRA-UMC-STUDIO's own WORKS/
  library** - `trajectory_panel.py` is a local-only point recorder today
  (records the selected robot's live joint pose, jogs back to a recorded
  point) - it does not read or write HYDRA-UMC-STUDIO's own
  `data/WORKS/*.json` trajectory file format yet, so a point recorded
  here isn't visible from a browser tab's own Works library. Real,
  scoped follow-up: reverse-engineer that JSON shape from HYDRA-UMC-STUDIO's
  own `src/examples/utils.ts`/`RobotDetail.tsx` and read/write the same
  files (accessible remotely once a `/api/works` style endpoint exists -
  today's REMOTE_API.md doesn't cover file-level access, only the full
  settings blob).
- **mDNS/Bonjour auto-discovery** - blocked on the same server-side gap
  `REMOTE_API.md`'s own "Future work" section already documents (no
  `_hydra-umc._tcp` service advertised yet). The subnet scan is the real,
  working option until that exists.
- **VPN-tunnel-specific UI** - deliberately NOT built as a separate
  feature. A VPN tunnel just makes a remote host reachable as if it were
  local - the existing "Add server by address" manual entry in the
  Server Browser panel already works through any tunnel that's already
  up, no VPN-aware code needed. If a real VPN-management need shows up
  later (bringing a tunnel up/down from inside the app, not just using
  one that's already connected), that's a genuinely separate feature to
  scope then, not something this pass silently half-built.
- **CAN-OTA flashing/testing from SUITE** - the same real gap
  `REMOTE_API.md` section 4 documents: HYDRA-UMC STUDIO's own Flasher/
  Tester run entirely client-side against a simulated transport, with no
  server-side endpoint for a remote client to drive. Revisit once that
  exists.
- **Real BLE/Bluetooth transport** - not applicable to SUITE (a desktop
  app reaching a HYDRA-UMC over the network) - see the 2 mobile control
  apps' own `docs/ARCHITECTURE.md` for that transport's own status.
