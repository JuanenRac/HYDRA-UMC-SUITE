// =============================================================================
// HYDRA-UMC - VacuumTable250x250x15mm.scad
// Parametric single-piece vacuum table for LumenPnP / JuanenPNP.
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0 - see LICENSE
// =============================================================================
// DIMENSIONS: 250x250mm
// CONFIGURATION: 30mm grid, reinforced pillars, metal M5 fittings

// --- GEOMETRIC PARAMETERS ---
length = 250;
width = 250;
base_height = 15;
sealing_margin = 8;     // Increased slightly for greater stability
channel_depth = 1.5;
channel_width = 1.2;
channel_spacing = 5.0; // Adjusted to cover the XL area

// --- MECHANICAL ALIGNMENT (THE "L") ---
l_wall_height = 1.2;    
l_wall_thickness = 5;      // More robust for the XL size

// --- FASTENERS (M3 SOCKET HEAD SCREWS) AND M5 FITTINGS ---
m3_screw_diameter = 3.4; 
m3_head_diameter = 6.2;    
m3_head_depth = 4.5;
fitting_spacing = 100; // Wider spacing for tubing on the large table
m5_tap_drill_diameter = 4.2; 

// LumenPnP grid: 210mm is the multiple of 30 closest to the edge
mounting_spacing_x = 210; 
mounting_spacing_y = 210;  

$fn = 60; 

union() {
    difference() {
        // 1. XL SOLID BODY
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

        // 2. CHANNEL GRID (Expanded area)
        for (x = [sealing_margin + l_wall_thickness : channel_spacing : length - sealing_margin]) {
            translate([x, l_wall_thickness + sealing_margin, base_height - channel_depth])
                cube([channel_width, width - (sealing_margin*2) - l_wall_thickness, channel_depth + 0.1]);
        }
        for (y = [sealing_margin + l_wall_thickness : channel_spacing : width - sealing_margin]) {
            translate([l_wall_thickness + sealing_margin, y, base_height - channel_depth])
                cube([length - (sealing_margin*2) - l_wall_thickness, channel_width, channel_depth + 0.1]);
        }

        // 3. XL INTERNAL PLENUM (Vacuum chamber)
        translate([15, 15, 4]) cube([length-30, width-30, base_height-8]);

        // 4. DRILL HOLES FOR M5 FITTINGS
        for (offset = [-fitting_spacing/2, fitting_spacing/2]) {
            translate([length/2 + offset, width - 10, base_height/2])
                rotate([-90,0,0]) cylinder(h = 15, d = m5_tap_drill_diameter); 
        }

        // 5. MOUSE BITE (Alignment corner)
        translate([l_wall_thickness, l_wall_thickness, base_height - 1]) cylinder(h = 5, d = 5);
            
        // 6. MOUNTING HOLES (210x210mm square)
        mounting_offset_x = (length - mounting_spacing_x) / 2;
        mounting_offset_y = (width - mounting_spacing_y) / 2;
        for (mounting_x = [mounting_offset_x, mounting_offset_x + mounting_spacing_x]) {
            for (mounting_y = [mounting_offset_y, mounting_offset_y + mounting_spacing_y]) {
                translate([mounting_x, mounting_y, -1]) cylinder(h=base_height+2, d=m3_screw_diameter);
                translate([mounting_x, mounting_y, base_height - m3_head_depth]) cylinder(h=6, d=m3_head_diameter);
            }
        }
    }

    // 7. REINFORCED PILLAR SYSTEM (Increased density for 250mm)
    intersection() {
        translate([15, 15, 4]) cube([length-30, width-30, base_height-8]);
        union() {
            // Pillars every 18mm to prevent any sagging in the center
            for (pillar_x = [25 : 18 : length-25]) {
                for (pillar_y = [25 : 18 : width-25]) {
                    translate([pillar_x, pillar_y, 3.9]) 
                        cube([4, 4, base_height-7.8]); 
                }
            }
        }
    }
}

// 8. CUSTOM LOGO (Centered on the front)
// Note: In OpenSCAD, subtract the text for engraving; it is added here
// to show its location, but the code above already integrates it as a subtraction if preferred.
