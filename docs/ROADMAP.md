# HYDRA-UMC SUITE - Roadmap / Honest Scope Statement

What's real today vs. deliberately left for a future pass, matching this
ecosystem's own established documentation convention of not overstating
what's implemented. Every item below is a genuine gap, not a hidden bug -
each one is a scoped, well-understood next step, not a redesign.

**Why login exists in `net/client.py` at all:** HYDRA-UMC STUDIO's server
requires a bearer token (`POST /api/login`) on every write and on the
`/ws` upgrade - GET reads have no such requirement, so a connection with
no token can still read state, but every write 401s and the WebSocket
upgrade is rejected outright (code 1008) until login succeeds. `net/client.py`
logs in automatically using the per-server credentials on `ServerInfo`
(`admin`/`admin` by default, matching every real HYDRA-UMC STUDIO server's
own seeded account - editable per-server from the Server Browser panel),
and retries on its own reconnect cadence if a login attempt fails. Re-verified
end-to-end against a real running server (`tests/smoke_test_app.py`) -
"SMOKE TEST PASSED", 8 real robots, `Connection status live: True`.

The WebSocket connection also opens with no message-size cap
(`max_size=None`): the server sends the FULL settings tree (1.6MB+ on a
populated swarm, and only grows with more robots/trajectory points) as the
first message on every connect, which exceeds the `websockets` library's
own default 1 MiB limit - a cap here would close the connection with code
1009 before a single byte of real state got through. No cap mirrors what a
browser WebSocket client does; the real fix for the underlying payload
size is a smaller wire format server-side, not a client-side ceiling that
just moves where it breaks.

## ✅ Real and verified end-to-end

- **Network discovery** (`hydra_suite/net/discovery.py`) - two independent
  paths running CONCURRENTLY, deduplicated by (host, port): a brute-force
  concurrent subnet scan hitting `GET /api/hydra-info` on every candidate
  host (the guaranteed fallback - works even where multicast doesn't), and
  real mDNS/Bonjour discovery (`discover_mdns()`, via the `zeroconf`
  package) against the actual `_hydra._tcp` service `server.ts` publishes
  (`bonjour-service`, `setupDiscovery()`) - near-instant when multicast
  delivery works, same service name HYDRA-UMC-IOS-CONTROL's own
  `discovery.dart` already queries. Every mDNS hit is still verified with
  the same real `GET /api/hydra-info` probe the subnet scan uses before
  being trusted - resolving a name is not the same as confirming a real
  server answers there. Both paths tested against a real running
  HYDRA-UMC STUDIO server. Identifies a real server by the *shape* of that
  endpoint's JSON payload (`remoteApiVersion`, `appVersion`, `hostname`,
  `controllerCount`, `robotCount` all present together), not by matching
  its `product` field against a fixed string - that field is actually the
  server's own user-editable display name (Config > Identity in the
  browser UI, defaults to "HYDRA-UMC STUDIO" only until renamed), so a
  literal-string check would stop recognizing any server the owner had
  ever renamed while still finding it fine by typing its IP in manually
  (which never checks that field at all).
- **Live connection** (`hydra_suite/net/client.py`) - REST read/write +
  WebSocket live sync, implementing
  [`HYDRA-UMC-SERVER/docs/REMOTE_API.md`](https://github.com/JuanenRac/HYDRA-UMC-SERVER/blob/main/docs/REMOTE_API.md)
  exactly (moved there from HYDRA-UMC-STUDIO's own docs/ when the headless
  backend was split out into its own repository - the contract itself
  didn't change, only which repo documents/hosts it). Verified: connects, receives real state (8 robots), pushes a
  joint change, receives the broadcast echo correctly suppressed. Per-server
  login success/failure is surfaced in the Server Browser panel (a distinct
  "Login failed" row status with the server's own rejection detail as a
  tooltip), not just logged silently - and username/password are editable
  per-server there too, both before and after adding a server.
- **Swarm support** (`hydra_suite/app.py`'s `SuiteController`) - holds an
  arbitrary number of simultaneous `HydraConnection`s, one per added
  server, with one "active" for the other panels to show. Connection and
  login status are broadcast for every server in the swarm, not just
  whichever one happens to be active, so the server list stays accurate
  for servers you aren't currently looking at too.
- **3D viewport** (`hydra_suite/render/`) - real forward kinematics for
  ALL 24 real robot models (`kinematics.py`'s own `ROBOT_REGISTRY`) -
  Parol6, Faze4, AR3, AR4, UR3e/5e/10e/16e/20, xArm6, Lite 6, e.DO, Gen3
  Lite, M-710iC, SO-ARM100, Gen2, PiPER, Z1, ViperX 300, WidowX 250,
  Koch v1.1, UR3/UR5/UR10 classic, numerically verified to match
  HYDRA-UMC-STUDIO's own TypeScript FK bit-for-bit: UR5e matches to
  849.7401073213356mm for its fully-extended horizontal reach, and
  Parol6/Faze4/AR3/AR4's "quaternion family" engine
  (`quat_family_link_transforms()`, arbitrary per-joint axes) matches the
  real TS output to 0.000000mm error across 3 test poses each
  (`tests/verify_all_kinematics.py`) - driving real STL meshes (`mesh.py`,
  the exact same files as HYDRA-UMC-STUDIO's own `public/models/<robot>/`)
  through a real OpenGL 3.3 core-profile shader pipeline (`viewport.py`).
  A 25th entry, "Generic (6-DOF)", has no STL at all - a primitive-built
  cylinder/box rig (`generic_rig.py`) ported 1:1 from HYDRA-UMC-STUDIO's
  own `GenericRobotArm.tsx`, for any robot with no dedicated mesh set.
  Verified with actual GL context creation, shader compile/link, and real
  paint passes for one robot from each of the 3 render families (UR5e,
  AR3, Generic) on this machine's real GPU driver
  (`tests/smoke_test_viewport.py`), not just unit-tested math. VBOs are
  built once per mesh and cached (never rebuilt per frame), uniform
  locations are resolved once at link time rather than re-queried by name
  on every draw call, and the viewport only schedules a repaint when the
  robot it's actually showing has a genuinely different pose than what's
  already on screen - not on every WebSocket push from anywhere else in
  the swarm, which is what made the view visibly laggy on a busy multi-robot
  server even though nothing about the displayed robot had changed.
- **Live 3D preview for all 5 tool-attachment modules that have one on
  STUDIO's own side** - CNC/Laser/Heated Bed/Vacuum Table
  (`render/module_rig.py` + `render/viewport.py`'s
  `set_attached_module()`, a real port of STUDIO's own per-panel
  `SharedModule3DView.tsx`: same box/cylinder shapes, positions, and hex
  colors at the same real mm-to-meter scale) and Pick & Place
  (`render/pnp_rig.py` + `set_attached_pnp()`, a real port of STUDIO's
  own `LumenPnPRig.tsx`: the 5 real `.stl` meshes in
  `assets/meshes/lumenpnp/`, posed through a real Cartesian-gantry chain,
  not primitives). Both modes are drawn by a `RobotViewport` instance
  embedded directly in the owning panel's own layout, live-updating on
  enable/disable and on every real edit (width/length for the primitive
  4; X/Y/Z/nozzle1/nozzle2 for Pick & Place).
- **Jog controls, Overview, Server Browser, local trajectory point
  recorder** - all read/write against the real live state of whichever
  server is active.
- **Photoshop-style dockable workspace** - real `QDockWidget`s (Qt's own
  mature docking system), not a custom-built one - float, dock, tab
  together, split, close, and re-show via the View menu all work because
  Qt itself already implements them correctly.
- **All 11 of 11 tool-attachment config panels** - CNC, Laser, Heated
  Bed, Vacuum Table, ATC (Automatic Tool Changer), XY Table, Rack
  Manager, Pick & Place, Kinematic Brain Stage (the controller-level
  gantry/heated-bed/ATC-revolver/conveyor/endstops/fans/pumps/valves
  state), Flasher, and Tester - real feature parity with every one of
  HYDRA-UMC-STUDIO's own tool-specific screens, each a faithful port of
  its real behavior (including STUDIO's own occasionally quirky
  behavior, reproduced on purpose rather than "fixed" here), each with
  its own real headless test coverage. See `README.md`'s own Features
  section for the per-panel breakdown.
- **CAN-OTA/SPI-OTA flashing and diagnostics** (`hydra_suite/can_ota.py`,
  a real port of HYDRA-UMC-STUDIO's own `src/lib/canOta.ts`) - `mock`
  transport simulates the whole protocol client-side (page-by-page
  flash progress, self-test, a raw CAN bus monitor); `hardware`
  transport reaches a REAL path for the Kinematic Brain and Robot
  Controller Board tiers via a new `HydraConnection.canota_request()`
  (`net/client.py`) against `HYDRA-UMC-SERVER`'s own
  `/api/hardware/canota/*` routes - the URTC Tool Head/Advanced
  Expansion tiers have no real relay tunnel yet on either client, an
  honest boundary reproduced from STUDIO's own source, not a gap
  specific to this app.
- **Real IP (RTSP) camera support alongside USB** - each camera's own
  Source Type toggle (USB / IP), with real, generic per-brand RTSP
  fields (host/port/path/credentials) - matches
  `HYDRA-UMC-VISION-STREAMER`'s own `CameraConfig(source_type=...)`
  one-to-one, plus real live MJPEG rendering (`iter_mjpeg_frames()`,
  `cameras_panel.py`) - a real client for the same proxied stream,
  scanning raw bytes for JPEG SOI/EOI markers directly (the same real,
  proven approach `HYDRA-UMC-ANDROID-CONTROL`'s own
  `MjpegStreamParser.kt` uses) rather than parsing the multipart
  boundary. Verified against a real local HTTP server serving a real
  multipart stream, including an oversized/corrupt frame being skipped
  without killing the feed.

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
- **VPN-tunnel-specific UI** - deliberately NOT built as a separate
  feature. A VPN tunnel just makes a remote host reachable as if it were
  local - the existing "Add server by address" manual entry in the
  Server Browser panel already works through any tunnel that's already
  up, no VPN-aware code needed. If a real VPN-management need shows up
  later (bringing a tunnel up/down from inside the app, not just using
  one that's already connected), that's a genuinely separate feature to
  scope then, not something this pass silently half-built.
- **Real BLE/Bluetooth transport** - not applicable to SUITE (a desktop
  app reaching a HYDRA-UMC over the network) - see the 2 mobile control
  apps' own `docs/ARCHITECTURE.md` for that transport's own status.
- **Atomic per-command sync** (`POST /api/robot/:id/command`) - the
  Android app sends every mutation (jog, valve, pump, tool, speed,
  play/pause/stop/enable/disable) through this endpoint instead of always
  pushing the full settings tree; this app's own `push_state()` still
  always does a full read-modify-write over WebSocket/REST for every
  change. `_handle_message()` already understands an incoming `"delta"`
  broadcast from another client using that endpoint, so a command sent
  that way by the Android app still shows up here live - this app just
  doesn't originate its own writes that way yet. Real gap, not urgent (the
  message-size handling above means a full-tree push at least doesn't
  crash the connection).
- **`combinedWith` (combined-robot mode)** - not exposed in this app's UI
  yet, despite being a real, shipping part of HYDRA-UMC-STUDIO's own
  data model and README. `RobotView` in `models.py` doesn't read/write
  this field yet.
