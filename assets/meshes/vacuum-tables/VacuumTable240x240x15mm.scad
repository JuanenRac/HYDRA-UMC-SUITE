// =============================================================================
// HYDRA-UMC - VacuumTable240x240x15mm.scad
// Parametric single-piece vacuum table for LumenPnP / JuanenPNP.
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0 - see LICENSE
// =============================================================================
// DIMENSIONS: 240x240mm (To avoid the exclusion zone)
// CONFIGURATION: 30mm grid, reinforced pillars, metal M5 fittings

// --- GEOMETRIC PARAMETERS ---
length = 240; 
width = 240;
base_height = 15;
sealing_margin = 8;     
channel_depth = 1.5;
channel_width = 1.2;
channel_spacing = 5.0; 

// --- MECHANICAL ALIGNMENT (THE "L") ---
l_wall_height = 1.2;    
l_wall_thickness = 5;      

// --- FASTENERS (M3 SOCKET HEAD SCREWS) AND M5 FITTINGS ---
m3_screw_diameter = 3.4; 
m3_head_diameter = 6.2;    
m3_head_depth = 4.5;
fitting_spacing = 100; 
m5_tap_drill_diameter = 4.2; 

// LumenPnP grid: 210mm (30mm * 7)
// This leaves a (240-210)/2 = 15mm margin on each side for the screws
mounting_spacing_x = 210; 
mounting_spacing_y = 210;  

$fn = 60; 

union() {
    difference() {
        // 1. SOLID BODY 240x240
        union() {
            cube([length, width, base_height]);
            // Alignment walls
            translate([0,0,base_height]) cube([length, l_wall_thickness, l_wall_height]);
            translate([0,0,base_height]) cube([l_wall_thickness, width, l_wall_height]);
            
            // Reinforcements for 2 M5 fittings
            for (offset = [-fitting_spacing/2, fitting_spacing/2]) {
                translate([length/2 + offset, width - 2, base_height/2])
                    rotate([-90,0,0]) cylinder(h = 2, d = 12); 
            }
        }

        // 2. CHANNEL GRID
        for (x = [sealing_margin + l_wall_thickness : channel_spacing : length - sealing_margin]) {
            translate([x, l_wall_thickness + sealing_margin, base_height - channel_depth])
                cube([channel_width, width - (sealing_margin*2) - l_wall_thickness, channel_depth + 0.1]);
        }
        for (y = [sealing_margin + l_wall_thickness : channel_spacing : width - sealing_margin]) {
            translate([l_wall_thickness + sealing_margin, y, base_height - channel_depth])
                cube([length - (sealing_margin*2) - l_wall_thickness, channel_width, channel_depth + 0.1]);
        }

        // 3. INTERNAL PLENUM (Vacuum chamber)
        translate([15, 15, 4]) cube([length-30, width-30, base_height-8]);

        // 4. DRILL HOLES FOR M5 FITTINGS
        for (offset = [-fitting_spacing/2, fitting_spacing/2]) {
            translate([length/2 + offset, width - 10, base_height/2])
                rotate([-90,0,0]) cylinder(h = 15, d = m5_tap_drill_diameter); 
        }

        // 5. MOUSE BITE
        translate([l_wall_thickness, l_wall_thickness, base_height - 1]) cylinder(h = 5, d = 5);
            
        // 6. FIXED MOUNTING HOLES (210x210mm)
        mounting_offset_x = (length - mounting_spacing_x) / 2;
        mounting_offset_y = (width - mounting_spacing_y) / 2;
        for (mounting_x = [mounting_offset_x, mounting_offset_x + mounting_spacing_x]) {
            for (mounting_y = [mounting_offset_y, mounting_offset_y + mounting_spacing_y]) {
                translate([mounting_x, mounting_y, -1]) cylinder(h=base_height+2, d=m3_screw_diameter);
                translate([mounting_x, mounting_y, base_height - m3_head_depth]) cylinder(h=6, d=m3_head_diameter);
            }
        }
        
        // 7. LOGO ENGRAVING (Front)
        translate([length/2, 2, base_height/2])
            rotate([90,0,0])
                linear_extrude(height = 3)
                    text("JuanenPNP", size = 10, font = "sans:style=Bold", halign = "center", valign = "center");
    }

    // 8. INTERNAL PILLARS (Optimized for 240mm)
    intersection() {
        translate([15, 15, 4]) cube([length-30, width-30, base_height-8]);
        union() {
            for (pillar_x = [25 : 19 : length-25]) {
                for (pillar_y = [25 : 19 : width-25]) {
                    translate([pillar_x, pillar_y, 3.9]) 
                        cube([4, 4, base_height-7.8]); 
                }
            }
        }
    }
}
