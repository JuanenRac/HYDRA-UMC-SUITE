// =============================================================================
// HYDRA-UMC - Parametric PCB rack: editable STL components and complete assembly
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0 - see LICENSE
// =============================================================================
// Millimeters, Z up. Width/depth describe the usable PCB envelope.
// Review tolerances, loads, material and robot clearances before fabrication.
part = 0; // 0=assembly, 1=base, 2=wall, 3=guide
rack_width = 160;
rack_depth = 160;
capacity = 24;
$fn = 24;
assert(rack_width >= 40 && rack_width <= 1000);
assert(rack_depth >= 40 && rack_depth <= 1000);
assert(capacity >= 1 && capacity <= 24 && floor(capacity) == capacity);
module rounded_plate(w,d,h,r=2) {
    hull() for(x=[r,w-r],y=[r,d-r])
        translate([x,y,0]) cylinder(h=h,r=r);
}
module base(w,d) {
    difference() {
        rounded_plate(w+20,d+20,20);
        for(x=[5,w+15],y=[5,d+15])
            translate([x,y,-1]) cylinder(h=22,d=4);
        // Shallow underside weight-saving pocket, retaining a solid floor.
        translate([15,15,-1]) cube([w-10,d-10,8]);
    }
}
module wall(d,h) { rounded_plate(10,d,h,1); }
module guide(d) { rounded_plate(4,d,3,0.6); }
if(part==1) base(160,160);
else if(part==2) wall(160,10);
else if(part==3) guide(160);
else if(part==0) {
    translate([-rack_width/2-10,-rack_depth/2-10,0]) base(rack_width,rack_depth);
    for(side=[-1,1]) {
        translate([side<0 ? -rack_width/2-10 : rack_width/2,-rack_depth/2,0])
            wall(rack_depth,capacity*10+40);
        for(i=[0:capacity-1])
            translate([side<0 ? -rack_width/2 : rack_width/2-4,-rack_depth/2,36+i*10])
                guide(rack_depth);
    }
} else assert(false,"Unknown rack component");
