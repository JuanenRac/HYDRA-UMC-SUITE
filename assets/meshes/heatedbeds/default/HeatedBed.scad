// =============================================================================
// HYDRA-UMC - Heated bed visualization, parametric 5 mm plate
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0 - see LICENSE
// Visualization only: not an electrical heater or a certified fabrication plan.
// =============================================================================
bed_width = 200;
bed_length = 200;
bed_thickness = 5; // Fixed across all presets.
corner_radius = 3;
$fn = 40;

assert(bed_width >= 25 && bed_length >= 25);
assert(bed_thickness == 5);

module rounded_plate(width, length, height, radius) {
    hull()
        for (x = [radius, width-radius])
            for (y = [radius, length-radius])
                translate([x,y,0]) cylinder(r=radius,h=height);
}

difference() {
    rounded_plate(bed_width, bed_length, bed_thickness, corner_radius);
    // Four through-holes and shallow counterbores, inside the nominal footprint.
    for (x = [8, bed_width-8])
        for (y = [8, bed_length-8]) {
            translate([x,y,-0.1]) cylinder(d=4.2,h=5.2);
            translate([x,y,4]) cylinder(d=7.2,h=1.1);
        }
    // Recessed perimeter marking: all detail stays BELOW the 5 mm top surface.
    translate([0,0,4.8])
        difference() {
            translate([5,5,0]) rounded_plate(bed_width-10,bed_length-10,0.3,2);
            translate([5.5,5.5,-0.1]) rounded_plate(bed_width-11,bed_length-11,0.5,1.5);
        }
    // Center alignment cross and engraved product name.
    translate([bed_width/2-6,bed_length/2-0.25,4.7]) cube([12,0.5,0.4]);
    translate([bed_width/2-0.25,bed_length/2-6,4.7]) cube([0.5,12,0.4]);
    translate([bed_width/2,bed_length/2+12,4.7])
        linear_extrude(0.4)
            text("HYDRA-UMC",size=min(7,bed_width/16),halign="center");
    // Underside grooves suggest a heater layout; they are NOT a resistor design.
    for (y = [15:10:bed_length-15])
        translate([12,y,-0.1]) cube([bed_width-24,0.8,0.35]);
}

