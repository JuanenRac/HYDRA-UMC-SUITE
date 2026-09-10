<!--
=============================================================================
HYDRA-UMC-SUITE - Vacuum table model catalog and rendering
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0 - see LICENSE
=============================================================================
-->
# Vacuum table models

## Select a model

Choose a robot, open **Vacuum Table**, enable the module and select its model.
The list contains six original JuanenPNP / HYDRA-UMC designs for use with LumenPnP:
160 × 120, 230 × 210, 230 × 250, 232 × 217, 240 × 240 and 250 × 250 mm.

All have a **15 mm base** and **16.2 mm total height** including the alignment walls.
The selector uses the CAD footprint: X is the first number and Y the second.
The size fields are read-only: stretching an STL would distort the holes and channels.
The existing placement/rotation and display-scale controls are separate; keep display
scale at 1 for a real-size layout. Reset selects 160 × 120 mm, resets placement and
sets pump and valve off, as part of the existing reset operation.

Selection changes geometry configuration only. It does not toggle the pump,
valve, robot movement or any physical output. Pump and valve controls retain their
existing behavior. A rendered table is not evidence of vacuum pressure or hardware
availability.

## Configuration and compatibility

Each robot keeps its selection in its existing settings block:

~~~json
{
  "vacuumTable": {
    "enabled": true,
    "modelId": "232x217x15",
    "size": { "width": 232, "length": 217 },
    "pumpActive": false,
    "valveActive": false,
    "worldPos": { "x": 0, "y": 0 },
    "worldRot": 0,
    "renderScale": 1
  }
}
~~~

STUDIO and SUITE use the same model IDs and catalog. This field travels through
their existing full-settings synchronization with SERVER; no new hardware command
or server endpoint is introduced. Writing settings still requires the existing
permissions and network connection. Test bidirectional sync with both updated
clients before deployment; an old client cannot render these new models.

A missing or unknown modelId displays the 160 × 120 mm model. Merely reading old
settings does not rewrite them. Enabling, selecting a valid model or resetting
writes the catalog ID and matching size. Old arbitrary sizes no longer deform the
geometry. Unknown IDs passed to the selection handler are ignored, never treated
as filesystem paths or remote URLs. Selecting a model preserves placement, pump,
valve and extension fields; it does not reset renderScale.

## Assets and coordinate system

assets/meshes/vacuum-tables contains catalog.json plus the six STL files and their matching SCAD
sources. STL files use **millimeters**, with a corner origin and CAD Z pointing up.
The renderers convert to meters, center the XY footprint, then rotate -90 degrees
about X into the applications' Y-up world. The table bottom stays at world Y=0.
The first CAD dimension maps to application width/X; the second maps to length
(depth in the Y-up viewport). No automatic "fit to old size" is performed.

STUDIO loads binary STL on demand in both the dedicated panel and robot-cell view;
a loading error is displayed without replacing the model with a fake table.
SUITE loads the same STL using its existing mesh loader, in the classic panel and
the Qt Quick vacuum-table preview. Drag to orbit and use the wheel to zoom.
An unavailable asset/OpenGL context is reported by the Qt Quick preview.

These are original user-authored designs, not Opulo's machine CAD. Export preserves
the supplied channels, cavities, pillars, mounting holes and any existing design
limitations. The model name describes base thickness, not overall wall height.
Rendering does not certify printability, airtightness, pillar bonding or mounting
compatibility; inspect each part in a slicer and validate the physical part.

## Regenerate a mesh

Install OpenSCAD separately for CAD work; users only viewing a table do not need it.
From the repository root (OpenSCAD on PATH):

~~~sh
openscad --export-format binstl -o assets/meshes/vacuum-tables/VacuumTable232x217x15mm.stl assets/meshes/vacuum-tables/VacuumTable232x217x15mm.scad
~~~

On Windows, invoke the installed executable with PowerShell's call operator:

~~~powershell
& "C:/Program Files/OpenSCAD/openscad.com" --export-format binstl -o "assets/meshes/vacuum-tables/VacuumTable232x217x15mm.stl" "assets/meshes/vacuum-tables/VacuumTable232x217x15mm.scad"
~~~

When a design changes, regenerate its mesh and update the corresponding assets in
both client repositories. Keep catalogs, dimensions and IDs identical. Publish
matching SCAD source with the mesh. Do not edit the STL by hand or export over a
production asset until the CAD change is reviewed. New model IDs require catalog,
UI compatibility and asset tests; localized labels/notes must cover seven languages.

## Verification

~~~sh
python -m unittest discover -s tests -p test_vacuum_tables.py
python tests/verify_module_config_panel.py
python verify_qt_suite_shell.py
~~~

Use QT_QPA_PLATFORM=offscreen for the UI logic tests on a headless machine. A real
OpenGL-capable session is needed to inspect rendered pixels.

These checks validate inventory, finite vertices, dimensions, orientation,
fallback handling and preservation of control fields without machine I/O.
They are not physical vacuum or safety tests.
