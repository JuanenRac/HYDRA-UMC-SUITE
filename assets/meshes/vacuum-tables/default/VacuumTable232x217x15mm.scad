// =============================================================================
// HYDRA-UMC - VacuumTable232x217x15mm.scad
// Parametric single-piece vacuum table for LumenPnP / JuanenPNP.
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0 - see LICENSE
// =============================================================================
// DIMENSIONS: 232x217mm
// CONFIGURATION: 30mm grid, recessed M3 socket head screws
// DESIGN: Specifically for Bambu Lab P1S

// --- GEOMETRIC PARAMETERS ---
length = 232; 
width = 217; 
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
m3_head_depth = 4.5; // Recessed head
fitting_spacing = 90; 
m5_tap_drill_diameter = 4.2;   // Tap drill size for M5

// --- MOUNTING GRID (Multiples of 30mm) ---
// Centered: 210mm along X (30x7) and 150mm along Y (30x5)
mounting_spacing_x = 210; 
mounting_spacing_y = 150; 

$fn = 60; 

// ============================================================
// PART CONSTRUCTION
// ============================================================

union() {
    difference() {
        // 1. SOLID BASE BODY
        union() {
            cube([length, width, base_height]);
            
            // Right-angle alignment walls (The "L")
            translate([0,0,base_height]) cube([length, l_wall_thickness, l_wall_height]);
            translate([0,0,base_height]) cube([l_wall_thickness, width, l_wall_height]);
            
            // Bosses/Reinforcements for M5 fittings (Front)
            for (offset = [-fitting_spacing/2, fitting_spacing/2]) {
                translate([length/2 + offset, width - 2, base_height/2])
                    rotate([-90,0,0]) cylinder(h = 2, d = 12); 
            }
        }

        // 2. SURFACE CHANNEL GRID (To distribute vacuum)
        for (x = [sealing_margin + l_wall_thickness : channel_spacing : length - sealing_margin]) {
            translate([x, l_wall_thickness + sealing_margin, base_height - channel_depth])
                cube([channel_width, width - (sealing_margin*2) - l_wall_thickness, channel_depth + 0.1]);
        }
        for (y = [sealing_margin + l_wall_thickness : channel_spacing : width - sealing_margin]) {
            translate([l_wall_thickness + sealing_margin, y, base_height - channel_depth])
                cube([length - (sealing_margin*2) - l_wall_thickness, channel_width, channel_depth + 0.1]);
        }

        // 3. INTERNAL PLENUM (Empty air chamber)
        translate([15, 15, 4]) 
            cube([length-30, width-30, base_height-8]);

        // 4. DRILL HOLES FOR M5 FITTINGS (Vacuum inlets)
        for (offset = [-fitting_spacing/2, fitting_spacing/2]) {
            translate([length/2 + offset, width - 10, base_height/2])
                rotate([-90,0,0]) cylinder(h = 15, d = m5_tap_drill_diameter); 
        }

        // 5. MOUSE BITE (Relief at the inner corner of the alignment walls)
        translate([l_wall_thickness, l_wall_thickness, base_height - 1]) 
            cylinder(h = 5, d = 5);
            
        // 6. FIXED MOUNTING HOLES (Recessed M3 socket head screws)
        mounting_offset_x = (length - mounting_spacing_x) / 2;
        mounting_offset_y = (width - mounting_spacing_y) / 2;
        for (mounting_x = [mounting_offset_x, mounting_offset_x + mounting_spacing_x]) {
            for (mounting_y = [mounting_offset_y, mounting_offset_y + mounting_spacing_y]) {
                // Through-hole for the screw shank
                translate([mounting_x, mounting_y, -1]) 
                    cylinder(h=base_height+2, d=m3_screw_diameter);
                // Recess to conceal the socket screw head
                translate([mounting_x, mounting_y, base_height - m3_head_depth]) 
                    cylinder(h=m3_head_depth + 0.1, d=m3_head_diameter);
            }
        }
        
        // 7. CUSTOM LOGO ENGRAVING (Front)
        translate([length/2, 0.5, base_height/2])
            rotate([90,0,0])
                linear_extrude(height = 3)
                    text("JuanenPNP 232x217mm", size = 8.0, font = "sans:style=Bold", halign = "center", valign = "center");
    }

    // 8. INTERNAL PILLAR STRUCTURE (Prevents the roof from collapsing)
    intersection() {
        // Restrict the pillars to the exact plenum area
        translate([15, 15, 4]) cube([length-30, width-30, base_height-8]);
        union() {
            // Grid of 4x4mm pillars spaced every 18mm
            for (pillar_x = [25 : 18 : length-25]) {
                for (pillar_y = [25 : 18 : width-25]) {
                    translate([pillar_x, pillar_y, 3.9]) 
                        cube([4, 4, base_height-7.8]); 
                }
            }
        }
    }
}
