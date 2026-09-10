// =============================================================================
// HYDRA-UMC - VacuumTable160x120x15mm.scad
// Parametric single-piece vacuum table for LumenPnP / JuanenPNP.
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0 - see LICENSE
// =============================================================================

// --- PARAMETERS ---
length = 160; width = 120; base_height = 15;
sealing_margin = 6; channel_depth = 1.5; channel_width = 1.2; channel_spacing = 4.5; 
l_wall_height = 1.2; l_wall_thickness = 4;
m3_screw_diameter = 3.4; m3_head_diameter = 6.2; m3_head_depth = 4.5;
fitting_spacing = 60; m5_tap_drill_diameter = 4.2; 
mounting_spacing_x = 120; mounting_spacing_y = 90; 

$fn = 60; 

// FINAL UNION: Body minus cavities, PLUS pillars
union() {
    difference() {
        // 1. SOLID BODY
        union() {
            cube([length, width, base_height]);
            translate([0,0,base_height]) cube([length, l_wall_thickness, l_wall_height]);
            translate([0,0,base_height]) cube([l_wall_thickness, width, l_wall_height]);
            for (offset = [-fitting_spacing/2, fitting_spacing/2]) {
                translate([length/2 + offset, width - 2, base_height/2])
                    rotate([-90,0,0]) cylinder(h = 2, d = 12); 
            }
        }

        // 2. SURFACE CHANNELS
        for (x = [sealing_margin + l_wall_thickness : channel_spacing : length - sealing_margin]) {
            translate([x, l_wall_thickness + sealing_margin, base_height - channel_depth])
                cube([channel_width, width - (sealing_margin*2) - l_wall_thickness, channel_depth + 0.1]);
        }
        for (y = [sealing_margin + l_wall_thickness : channel_spacing : width - sealing_margin]) {
            translate([l_wall_thickness + sealing_margin, y, base_height - channel_depth])
                cube([length - (sealing_margin*2) - l_wall_thickness, channel_width, channel_depth + 0.1]);
        }

        // 3. PLENUM (THE CAVITY)
        translate([12, 12, 4]) cube([length-24, width-24, base_height-8]);

        // 4. M5 FITTING HOLES
        for (offset = [-fitting_spacing/2, fitting_spacing/2]) {
            translate([length/2 + offset, width - 10, base_height/2])
                rotate([-90,0,0]) cylinder(h = 15, d = m5_tap_drill_diameter); 
        }

        // 5. MOUSE BITE
        translate([l_wall_thickness, l_wall_thickness, base_height - 1]) cylinder(h = 5, d = 4.5);
            
        // 6. FIXED MOUNTING HOLES
        mounting_offset_x = (length - mounting_spacing_x) / 2;
        mounting_offset_y = (width - mounting_spacing_y) / 2;
        for (mounting_x = [mounting_offset_x, mounting_offset_x + mounting_spacing_x]) {
            for (mounting_y = [mounting_offset_y, mounting_offset_y + mounting_spacing_y]) {
                translate([mounting_x, mounting_y, -1]) cylinder(h=base_height+2, d=m3_screw_diameter);
                translate([mounting_x, mounting_y, base_height - m3_head_depth]) cylinder(h=6, d=m3_head_diameter);
            }
        }
    }

    // 7. PILLARS (Added HERE so the plenum subtraction does not remove them)
    // Place them inside an intersection block to keep them within the plenum area
    intersection() {
        translate([12, 12, 4]) cube([length-24, width-24, base_height-8]);
        union() {
            for (pillar_x = [25 : 20 : length-25]) {
                for (pillar_y = [25 : 20 : width-25]) {
                    translate([pillar_x, pillar_y, 3.9]) // Small bottom overlap
                        cube([4, 4, base_height-7.8]); // Small top overlap
                }
            }
        }
    }
}
