<!--
=============================================================================
HYDRA-UMC - Configurable STL PCB racks
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0 - see LICENSE
=============================================================================
-->

# Configurable input and output racks

## Configuration and compatibility

Each robot retains two independent racks, rack1 and rack2. Their Input/Output/None
roles, usable slots, base pickup pose and scene placement keep their existing
meaning. Editing geometry does not move a robot, recalibrate pickup coordinates
or change occupancy. Slot indicators describe usability, not physical occupancy.

| Field in rackSystem.rack1 / rack2 | Contract |
| --- | --- |
| width | Usable PCB width, integer 40–1000 mm, UI step 1 mm |
| depth | Usable PCB depth, integer 40–1000 mm, UI step 1 mm |
| capacity | Existing 1–24 plates, one guide level per plate |
| color | Optional #RRGGBB material override |
| usableSlots | Existing slot availability; retained when capacity changes |

Legacy configurations without geometry fields display 160 × 160 mm. Missing or
invalid geometry uses the same fallback in both clients without silently rewriting
saved settings. Input defaults blue (#0ea5e9), Output green (#10b981).
The color is external metadata: standard STL has no portable color channel.

The existing reset operation resets **both** racks, not only the card containing
the button. It restores 24 slots and the default geometry/colors. Geometry edits
alone retain the other rack and the robot's pickup pose.

## Geometry and coordinates

Three real STL components build the assembly:

- base.stl: reference CAD extent 180 × 180 × 20 mm.
- wall.stl: reference CAD extent 10 × 160 × 10 mm; two walls.
- guide.stl: reference CAD extent 4 × 160 × 3 mm; two guides per level.
- assembly.stl: complete default 160 × 160 mm usable / 24-slot rack.
- Rack.scad: editable, parametric OpenSCAD source for components and assembly.

Usable width/depth exclude the structure. Outer footprint is (width + 20) ×
(depth + 20) mm. Height is capacity × 10 + 40 mm. The base remains 20 mm thick
and walls 10 mm wide; height changes do not stretch slot spacing. Guide top is
39 + 10 × slotIndex mm, with a 2 mm plate indicator centered at 40 + 10 × slotIndex.
This preserves the former visualization's 10 mm pitch and first plate height.

STL uses CAD millimeters / Z-up. Clients center components, convert to meters /
Y-up, then assemble them. Mesh caches are never modified. Width/depth changes
scale appropriate component axes, with normal correction in SUITE.

These are visualization assets, not verified manufacturing drawings. Clearances,
PCB fit, thermal suitability, material strength, fasteners and robot calibration
require physical validation. Do not assume a graphical rack change updates a
robot's real trajectory or slot pickup positions.

## Using and editing the assets

Assets: assets/meshes/racks/. Source contract: hydra_suite/racks.py.

STUDIO offers independent 3D previews on both rack cards and reuses the same
assembly in its existing cell view. SUITE classic offers a preview per rack;
Qt Quick has a shared preview with a Preview rack button on each card, orbit and
zoom. SUITE slot indicators are opaque; STUDIO uses translucent indicators.

The STUDIO STL download is the **default** assembly, explicitly labelled
160 × 160 / 24, not a dynamic export of the current controls. Custom UI dimensions
are saved settings. For a custom complete STL, regenerate from OpenSCAD:

~~~sh
openscad --export-format binstl -D rack_width=161 -D rack_depth=201 -D capacity=6 -o Rack161x201-6.stl Rack.scad
~~~

On Windows use the full path to openscad.com if it is not on PATH.
Numeric part selects export mode: 0 complete assembly (default), 1 base, 2 wall,
3 guide. Component exports deliberately use reference dimensions independent of
rack_width/depth/capacity; the apps resize these reusable pieces.

To customize the live appearance, edit base.stl, wall.stl or guide.stl while
preserving their reference bounding boxes and orientation, or edit Rack.scad
and re-export each with -D part=1 / 2 / 3. Copy the matching assets into both
clients and restart/rebuild to clear cached meshes. Editing assembly.stl alone
does not change the live modular preview. Features such as holes scale in the
preview; for fabrication use a separately reviewed parametric assembly export.

## Synchronization and checks

SERVER stores the fields through its existing authenticated settings API.
The new fields need updated clients to display them. An already deployed web
bundle does not update until the new STUDIO build and assets are deployed.

Use the project's Python environment with its dependencies installed:

~~~sh
python tests/verify_rack_geometry.py
python tests/verify_rack_config_panel.py
python verify_qt_suite_shell.py
~~~

Tests cover finite mesh bounds/normals, nine size/capacity combinations,
fixed pitch, color fallback, independent rack edits and settings roundtrips.
They do not operate hardware. No new physical control or firmware command is
introduced.

