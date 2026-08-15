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
- **3D viewport** (`hydra_suite/render/`) - real forward kinematics for
  ALL 24 real robot models (`kinematics.py`'s own `ROBOT_REGISTRY`) -
  the original 9 (Parol6, Faze4, AR3, AR4, UR3e/5e/10e/16e/20) plus 15
  added since across several rounds (xArm6, Lite 6, e.DO, Gen3 Lite,
  M-710iC, SO-ARM100, Gen2, PiPER, Z1, ViperX 300, WidowX 250, Koch v1.1,
  UR3/UR5/UR10 classic),
  numerically verified to match HYDRA-UMC-STUDIO's own TypeScript FK
  bit-for-bit: UR5e matches to 849.7401073213356mm for its fully-extended
  horizontal reach, and Parol6/Faze4/AR3/AR4's "quaternion family" engine
  (`quat_family_link_transforms()`, arbitrary per-joint axes) matches the
  real TS output to 0.000000mm error across 3 test poses each
  (`tests/verify_all_kinematics.py`) - driving real STL meshes (`mesh.py`,
  the exact same files as HYDRA-UMC-STUDIO's own `public/models/<robot>/`)
  through a real OpenGL 3.3 core-profile shader pipeline (`viewport.py`).
  A 10th entry, "Generic (6-DOF)", has no STL at all - a primitive-built
  cylinder/box rig (`generic_rig.py`) ported 1:1 from HYDRA-UMC-STUDIO's
  own `GenericRobotArm.tsx`, for any robot with no dedicated mesh set.
  Verified with actual GL context creation, shader compile/link, and real
  paint passes for one robot from each of the 3 render families (UR5e,
  AR3, Generic) on this machine's real GPU driver
  (`tests/smoke_test_viewport.py`), not just unit-tested math.
- **Jog controls, Overview, Server Browser, local trajectory point
  recorder** - all read/write against the real live state of whichever
  server is active.
- **Photoshop-style dockable workspace** - real `QDockWidget`s (Qt's own
  mature docking system), not a custom-built one - float, dock, tab
  together, split, close, and re-show via the View menu all work because
  Qt itself already implements them correctly.

## 🚧 Deliberately out of scope this pass

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
