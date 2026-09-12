<!--
=============================================================================
HYDRA-UMC - Heated bed STL catalog and footprint configuration
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0 - see LICENSE
=============================================================================
-->
# Heated bed models

## Selection and dimensions

Open Heated Bed, select a robot and enable its module. Four presets are available:
100 × 100, 200 × 100, 200 × 200 and 255 × 255 mm. All have exactly **5 mm total
height**, including the engraved details. The default/reset preset is 200 × 200 mm.

Width and length have 5 mm arrow steps; integer dimensions from 25 to 5000 mm can
also be typed. Only the footprint changes: the vertical scale stays at one.
Selecting a preset restores both of its original dimensions. Editing size or
selecting a preset preserves placement, target temperature, thermistor readings
and SSR state. Disable/re-enable retains dimensions. Reset retains the existing
reset behavior (target 60 °C, SSR off, placement reset); it is not merely selection.

These are visual CAD assets, not a validated heater, resistor layout or fabrication
drawing. Holes and engravings scale with the viewport footprint. The application
does not regenerate manufacturing STL on each edit. Do not interpret the depicted
color as a measured material or temperature.

## Shared settings contract

~~~json
{
  "heatedBed": {
    "enabled": true,
    "modelId": "255x255x5",
    "size": { "width": 260, "length": 150 },
    "targetTemp": 60,
    "currentTemp1": 25,
    "currentTemp2": 25,
    "ssrActive": false,
    "worldPos": { "x": 0, "y": 0 },
    "worldRot": 0,
    "renderScale": 1
  }
}
~~~

The ordinary authenticated SERVER settings write persists these fields. No new
hardware command is introduced. Keep display renderScale=1 for the stated height.
Missing/unknown modelId uses 200x200x5, but valid saved sizes remain in effect
because heated-bed sizes were already configurable. Invalid dimensions fall back
to the selected catalog footprint. Invalid IDs passed to selection are ignored,
never interpreted as file paths. Reading settings does not rewrite them.

STUDIO's panel and cell view, SUITE's classic panel and its Qt Quick preview use
the same catalog and STL. SERVER's hosted STUDIO needs the updated client build;
changing server documentation alone does not update a deployed web UI. Older
clients can display the old primitive and should be upgraded together.

## Geometry and source

The plate has rounded corners, four through-holes with shallow counterbores,
recessed perimeter marks, a center cross, HYDRA-UMC engraving and underside grooves.
Every detail is cut into the plate, so nothing protrudes above 5 mm.
The underside grooves are visual detail, not an electrical design.

assets/meshes/heated-beds contains catalog.json, HeatedBed.scad and four preset STL files.
SCAD/STL coordinates are millimeters with a corner origin and Z up. Renderers
convert to meters, center the footprint and rotate to Y up: world bottom=0,
top=0.005 m. Cached source meshes are not mutated during resizing.

## Regeneration

OpenSCAD is needed only to regenerate CAD, not to run the application.
From this repository root:

~~~sh
openscad --export-format binstl -D bed_width=255 -D bed_length=255 -o assets/meshes/heated-beds/HeatedBed255x255x5mm.stl assets/meshes/heated-beds/HeatedBed.scad
~~~

On Windows use the installed openscad.com with PowerShell's call operator:
~~~powershell
& "C:/Program Files/OpenSCAD/openscad.com" --export-format binstl -D "bed_width=255" -D "bed_length=255" -o "assets/meshes/heated-beds/HeatedBed255x255x5mm.stl" "assets/meshes/heated-beds/HeatedBed.scad"
~~~

bed_thickness is fixed at 5. For new manufacturing dimensions, regenerate from
the parameterized source rather than stretching an exported mesh, and independently
review mounting and physical suitability. Keep both client catalogs/assets aligned.

## Verification

~~~sh
python tests/verify_heated_beds.py
python tests/verify_module_config_panel.py
python verify_qt_suite_shell.py
~~~

Tests check four real STL bounding boxes, 5 mm height, valid geometry, custom
footprints and preservation of heater/placement state. SERVER's existing
tools/verify_robot_command_contract.mjs tests preset/custom settings roundtrips
and another robot's isolation. None of these tests energizes a heater.

