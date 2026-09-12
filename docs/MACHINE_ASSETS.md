<!--
=============================================================================
HYDRA-UMC - Independent machine mesh assets
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0 - see LICENSE
=============================================================================
-->

# Independent machine models

## Selection and ownership

| Module key | Asset folder | STUDIO format | SUITE format |
| --- | --- | --- | --- |
| lumenPnP | lumenpnp | Original GLB | Original STL |
| juanenPnP | juanenpnp | STL | STL |
| juanenCNC | juanencnc | STL | STL |
| juanenLaser | juanenlaser | STL | STL |

Asset root in this project: assets/meshes/.

Each derivative started as an independent copy of all 167 original STL files
(7 articulated groups plus 160 individual parts), with parts/manifest.json and
ATTRIBUTION.txt preserved. These are ordinary files, not symlinks or aliases.
There is no automatic resynchronization with LumenPnP. Future edits may differ;
tests check completeness/parsing, not continued equality with the original.

CNC and laser now show the copied assembly instead of the old primitive frame.
They initially still look like LumenPnP, including its toolheads and feeders.
This is a visual starting point for owner-designed machines, not a claim of
completed CNC spindle, laser optics, guarding, hardware support or certification.

## Editing a variant

1. Choose the matching directory above. Never modify lumenpnp to customize a
   Juanen machine.
2. Edit the relevant .stl in that directory, preserving its filename, CAD
   millimeter units, Z-up orientation and existing assembly coordinates.
3. Keep the original pivot/origin for articulated meshes. A changed pivot needs
   matching rig/kinematic changes; do not center each exported part independently.
4. Restart/reload the application to clear cached geometry. STUDIO derivatives
   load STL directly, so editing them does **not** require GLB conversion.
5. If both clients are used, copy your edited variant into the corresponding
   directory of the other client. They deliberately have independent local files.

Root meshes:
base, y_carriage, x_carriage, z_carriage_left, z_carriage_right,
nozzle_left and nozzle_right. Additional assemblies are under parts/.
Filename-to-parent mappings remain in LumenPnPRig.tsx (STUDIO) and pnp_rig.py
(SUITE). Adding/removing/renaming meshes requires updating these lists as well
as the documentation/tests. A missing file must be repaired, not silently
replaced by a LumenPnP file.

The 7 root meshes and individual parts can overlap in the inherited source
assembly; inspect which visible component owns the feature you want to change.
Keep source attribution and mark your own modifications in VARIANT.md.
Copied manifest bounding boxes/triangle counts describe the original export;
update that metadata if it is used after editing the geometry.

## Behavior preserved and limits

PnP axis X/Y/Z and nozzle rotations still use the shared Cartesian hierarchy,
including separate translating Z sliders and rotating nozzle barrels.
Only the source directory changes. CNC/laser use the same initial hierarchy at
rest; this change does not add motion commands or change the server's module keys.
Input settings, enable/disable, world placement and role selection are retained.

The fixed CAD dimensions now determine CNC/laser appearance, just as for PnP.
Legacy size.width/length values remain stored/editable for compatibility but
do not stretch the assembly. Change the STL for actual geometry changes.
Existing outer renderScale remains a visual scene transform, not calibration.

STUDIO only preloads the selected machine's set, without synchronous vertex
merging. Per-machine URL caching keeps variants separate. LumenPnP retains
its established GLB loading path. No stale GLB duplicates are shipped for the
three editable variants. SUITE caches GPU buffers by directory, not one shared
LumenPnP key. Selection therefore cannot reuse another machine's modified mesh.

STUDIO uses the same renderer in menu previews and the cell view.
SUITE classic previews and Qt Quick previews select the appropriate directory.
STL assets retain the current application materials; standard STL does not
provide a portable color channel.

## Verification and publishing

Use the project's Python environment:

~~~sh
python tests/verify_machine_assets.py
python tests/verify_pick_and_place_panel.py
python tests/verify_module_config_panel.py
python verify_qt_suite_shell.py
~~~

The tests load all referenced STL files, verify finite geometry, validate
independent paths and ensure that CNC/laser use the mesh renderer. They allow
future variant modifications. No hardware is operated.

Commit/deploy each new asset folder together with its loader changes. A server
still serving an older STUDIO bundle will retain the old appearance until that
bundle and its model assets are updated. This work does not deploy to CM5.

See ATTRIBUTION.txt in each directory for the retained upstream export provenance
and licensing details. HYDRA-UMC wrapper code does not replace upstream rights.

