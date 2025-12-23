//Tilt Mount
use <./shared/Chamfer-Fillet-Machine.scad>

usb_cam_width = 38;// mm
usb_cam_height = 38;// mm
rpi_cam_width = 25;// mm
rpi_cam_height = 24;// mm
pcb_thickness = 2;//mm
con_gap_dim = 12;//mm
mesh_clearance = 0.15;//fmly 0.1 too tight, 0.5 very slack, 0.2 slack
eff_wheel_radius = 7.5;
eff_worm_radius = 4.375 + mesh_clearance;
wheel_thickness = 5.34;
worm_length = 12;
wheel_hub_radius = 3;
hub_dia = 6;
//clearence bores printed horizontally - distortion shrinks
clearance_bore = 5.65;//mm
//interference bores printed vertically - no distortion
interference_bore = 5.6;//mm
hex_hole_dia = 5.3;//hex shaft inside interference bore fit
plate_width = 44;// 38 + 6 wheel thickness mm
rpi_plate_width = 31;// 25 + 6 wheel thickness mm
eff_plate_height = 46;//mm
plate_height = 42.5;//mm
rpi_plate_height = 31;//mm
usb_h_hole_centres = 28;//mm
usb_v_hole_centres = 28;//mm
usb_h_hole_offset = 5;//mm
usb_v_hole_offset = 5;//mm
usb_hole_dia = 2;//mm
rpi_h_hole_centres = 21;//mm
rpi_v_hole_centres = 12.5;//mm
rpi_h_hole_offset = 2;//mm
rpi_v_hole_offset = 2;//mm
rpi_hole_dia = 2;//mm
plate_thickness = 4;// mm
recess = 4.5;//mm

bush_height = 2;
bush_dia = 5;
bush_hole_dia = 1.9;//M2 tapping size 1.6 plus vertical droop allowance
lug_thickness = 2;//mm
lug_dia = 6;//mm
lug_hole_dia = 3;//mm
bkt_wall_thickness = 3;
plate_bkt_gap = 3.0;//at either side
spacer_dia = 6.5;
bkt_width = plate_width + (2 * plate_bkt_gap);//wider bracket needed to accomodate worm!
bkt_height = 20;
bkt_depth = worm_length + 1.0;//mm

spigot_dia = 5;
spigot_length = bkt_wall_thickness*2;
shoulder_length = 3;//mm
shoulder_dia = 4;//mm
fix_hole_dia = 4.5;//mm

//find centre of plate
cx_offset = (plate_width - wheel_thickness)/2 + wheel_thickness/2;
cz_offset = eff_plate_height/2 + eff_wheel_radius;
ref_hole_offset_x = cx_offset - (usb_h_hole_centres/2);
ref_hole_offset_z = cz_offset + (usb_v_hole_centres/2);

rpi_cx_offset = (rpi_h_hole_centres - wheel_thickness)/2 + wheel_thickness/2 + 8;
rpi_cz_offset = rpi_v_hole_centres/2 + eff_wheel_radius + 24.5;// - 2.3;
rpi_hole_offset_radius = (sqrt(rpi_h_hole_centres^2 + rpi_v_hole_centres^2))/2;
echo("rpi_h_hole_centres", rpi_h_hole_centres, "rpi_v_hole_centres", rpi_v_hole_centres, "rpi_hole_offset_radius", rpi_hole_offset_radius);

module case() {
    wall_thickness = 2;//mm
    eff_width = 138;//mm
    eff_length = 66;//mm
    eff_depth = 35;//mm
    difference() {
        cube([eff_width + (2 * wall_thickness), eff_length + (2 * wall_thickness), eff_depth + wall_thickness], center=true);
        translate([0, 0, -wall_thickness]) cube([eff_width, eff_length, eff_depth], center=true);
        //cable hole
        translate([eff_width/2 - 25, -eff_length/2, 0]) rotate([90, 0, 0]) cylinder(h=10, d=20, $fn=32, center=true);
        //case fixing slot
        translate([-eff_width/2 + 25, -eff_length/2, 0]) {
            rotate([90, 0, 0]) cylinder(h=10, d=6, $fn=32, center=true);
            translate([0, 0, -10]) cube([6, 6, 20], center=true);
        }
        //bracket fixing hole
        translate([0, eff_length/2, -10]) rotate([90, 0, 0]) cylinder(h=10, d=6, $fn=32, center=true);
    }
}

module camera(width, height, thickness, h_hole_centres, v_hole_centres, h_hole_offset, v_hole_offset, hole_dia) {
    //relative to top-left mounting hole
    translate([-v_hole_offset, 0, -height + v_hole_offset]) difference() {
        cube([width, thickness, height], center=false);
        //rpi holes
        //relative to pcb
        translate([h_hole_offset, 0, height - (v_hole_centres + v_hole_offset)]) {
            //relative to origin
            translate([0, 0, 0]) rotate([90, 0, 0]) cylinder(h=thickness*3, d=hole_dia, center=true, $fn=32);
            translate([h_hole_centres, 0, 0]) rotate([90, 0, 0]) cylinder(h=thickness*3, d=hole_dia, center=true, $fn=32);
            translate([h_hole_centres, 0, v_hole_centres]) rotate([90, 0, 0]) cylinder(h=thickness*3, d=hole_dia, center=true, $fn=32);
            translate([0, 0, v_hole_centres]) rotate([90, 0, 0]) cylinder(h=thickness*3, d=hole_dia, center=true, $fn=32);
        }
    }    
}
module bush() {
    rotate([90, 90, 0]) {
        translate([0, 0, (plate_thickness + bush_height)/2 - recess]) cylinder(h=bush_height, d1=bush_dia, d2=bush_dia/2, center=true, $fn=32);
        }
}
module back_bush() {
    rotate([90, 90, 0]) {
        translate([0, 0, (bush_height/2) - recess - plate_thickness]) cylinder(h=bush_height, d2=bush_dia, d1=bush_dia/2, center=true, $fn=32);
        }
}
module fixhole() {
    rotate([90, 90, 0]) {
        cylinder(h=plate_thickness*4, d=bush_hole_dia, center=true, $fn=32);
    }
}
module usb_camera() {
    camera(usb_cam_width, usb_cam_height, pcb_thickness, usb_h_hole_centres, usb_v_hole_centres, usb_h_hole_offset, usb_v_hole_offset, usb_hole_dia);
}
module rpi_camera() {
    camera(rpi_cam_width, rpi_cam_height, pcb_thickness, rpi_h_hole_centres, rpi_v_hole_centres, rpi_h_hole_offset, rpi_v_hole_offset, rpi_hole_dia);
}
module rpi_zero() {
    //clockwise corners
    corner_radius = 3.5;//mm
    h_hole_centres = 58;//mm
    v_hole_centres = 23;//mm
    width = h_hole_centres + (2 * corner_radius);
    length = v_hole_centres + (2 * corner_radius);
    echo("rpi zero width x length mm", width, length);
    gpio_width = 50;//mm
    gpio_length = 5;//mm
    gpio_height = 9;//mm
    corners = [
        //x, y, r
        [0, 0, corner_radius],
        [0, length, corner_radius],
        [width, length, corner_radius],
        [width, 0, corner_radius]
    ];
    difference() {
        color("green") linear_extrude(pcb_thickness) chamfer_fillet_2d(corners);
        translate([corner_radius, corner_radius]) union() {
            translate([0, 0]) cylinder(h=pcb_thickness*3, d=rpi_hole_dia, $fn=32, center=true);
            translate([h_hole_centres, 0]) cylinder(h=pcb_thickness*3, d=rpi_hole_dia, $fn=32, center=true);
            translate([h_hole_centres, v_hole_centres]) cylinder(h=pcb_thickness*3, d=rpi_hole_dia, $fn=32, center=true);
            translate([0, v_hole_centres]) cylinder(h=pcb_thickness*3, d=rpi_hole_dia, $fn=32, center=true);
        }
    }
    //camera connector
    color("white") translate([1.5, (length/2), pcb_thickness + 0.75]) cube([3, 20, 1.5], center=true);
    //power
    color("silver") translate([11, 28, pcb_thickness + 1]) cube([7, 5, 2], center=true);
    //usb 7x5x2
    color("silver") translate([23.6, 28, pcb_thickness + 1]) cube([7, 5, 2], center=true);
    //hdmi
    color("silver") translate([52.6, 27, pcb_thickness + 1.5]) cube([12, 7, 3], center=true);
    //gpio
    color("black") translate([width/2, (gpio_length/2) + 1, (gpio_height/2) + pcb_thickness]) cube([gpio_width, gpio_length, gpio_height], center=true);
}
module rpi_clip(incl_base=false) {
    
    base_width = 13.0;
    base_length = 30.5;
    base_thickness = 2;
    usb_hdmi_gap_centre = 37.5;
    rpi_length = 30;
    clip_height = 6;
    clip_width = 3;
    clip_pcb_slot_height = 2;
    clip_fixed_pcb_slot_width = 1.0;
    clip_flex_pcb_slot_width = 1.5;
    clip_pin_clearance = 2;
    clip_tolerance = 1.0125;//expansion
    
    seat_height = clip_pin_clearance;
    roof_height = clip_pcb_slot_height + clip_pin_clearance;
    echo("seat_height:", seat_height, "roof_height:", roof_height);
    
    slot_fixed_offset = clip_width - clip_fixed_pcb_slot_width;
    slot_flex_offset = clip_width - clip_flex_pcb_slot_width;
    
    fixed_profile = [
        [0, 0],
        [0, clip_height],
        [clip_width, clip_height],
        [clip_width, (roof_height + clip_height)/2],
        [slot_fixed_offset, roof_height],
        [slot_fixed_offset, seat_height],
        [clip_width, seat_height],
        [clip_width, 0]
    ];
    flex_profile = [
        [0, 0],
        [0, clip_height],
        [slot_flex_offset + 0.5, clip_height],
        [slot_flex_offset + 0.5, roof_height],
        [slot_flex_offset, roof_height],
        [slot_flex_offset, seat_height],
        [clip_width, seat_height],
        [clip_width, 0]
    ];
    //base?
    translate([usb_hdmi_gap_centre, 0, -(pcb_thickness/2) - clip_pin_clearance]) {
        if (incl_base) translate([0, rpi_length/2, 0]) cube([base_width, base_length + slot_fixed_offset + slot_flex_offset, base_thickness], center=true);
        translate([-base_width/2, 0, base_thickness/2]) {
            rotate([90, 0, 90]) {
                union() {
                    translate([-slot_fixed_offset, 0, 0]) linear_extrude(base_width) polygon(fixed_profile);
                    translate([(rpi_length + clip_flex_pcb_slot_width) * clip_tolerance, 0, 0]) linear_extrude(base_width) mirror([1, 0, 0]) polygon(flex_profile);
                }
            }
        }
    }
}
module mount() {
    difference() {
        union() {
            //wheel gear from worm & wheel
            translate([0, 0, 0]) rotate([0, 90, 0]) import("shared/worm-wheel-wheel.stl", convexity=10);
            //collar
            translate([-(wheel_thickness + plate_bkt_gap)/2, 0, eff_wheel_radius]) rotate([0,90,0]) cylinder(h=plate_bkt_gap, r=eff_wheel_radius+0.5, $fn=32, center=true);
            //backplate
            translate([(plate_width - wheel_thickness)/2, recess, plate_height/2 + eff_wheel_radius - 2.3]) cube([plate_width, plate_thickness, plate_height], center=true);
            //fillet
            translate([-(wheel_thickness+plate_bkt_gap)/2,recess,plate_height/2 + eff_wheel_radius - 2.3]) cube([plate_bkt_gap, plate_thickness, plate_height], center=true);
            //standoff bushes
            //common shared top-left
            translate([ref_hole_offset_x, 0, ref_hole_offset_z]) bush();
            //rpi
            translate([ref_hole_offset_x + rpi_h_hole_centres, 0, ref_hole_offset_z]) bush();
            translate([ref_hole_offset_x + rpi_h_hole_centres, 0, ref_hole_offset_z - rpi_v_hole_centres]) bush();
            translate([ref_hole_offset_x, 0, ref_hole_offset_z - rpi_v_hole_centres]) bush();
            //usb
            translate([ref_hole_offset_x + usb_h_hole_centres, 0, ref_hole_offset_z]) bush();
            translate([ref_hole_offset_x + usb_h_hole_centres, 0, ref_hole_offset_z - usb_v_hole_centres]) bush();
            translate([ref_hole_offset_x, 0, ref_hole_offset_z - usb_v_hole_centres]) bush();
            //shaft spacer
            translate([plate_width - (wheel_thickness - plate_bkt_gap)/2, 0, eff_wheel_radius]) rotate([0, 90, 0]) cylinder(h=plate_bkt_gap, d=spacer_dia, $fn=32, center=true);
            //shaft spigot
            translate([plate_width - (wheel_thickness - spigot_length)/2, 0, eff_wheel_radius]) rotate([0, 90, 0]) cylinder(h=spigot_length, d=spigot_dia, $fn=32, center=true);
            //shaft
            translate([(plate_width-wheel_thickness)/2, 0, eff_wheel_radius]) rotate([0, 90, 0]) cylinder(h=plate_width, d=spacer_dia, $fn=32, center=true);
            //rpi zero clip
            translate([-36.75, 8, 45]) rotate([-90, 0, 0]) rpi_clip();
        }             
        //mounting holes
        //common shared top-left
        translate([ref_hole_offset_x, 0, ref_hole_offset_z]) fixhole();
        //rpi
        translate([ref_hole_offset_x + rpi_h_hole_centres, 0, ref_hole_offset_z]) fixhole();
        translate([ref_hole_offset_x + rpi_h_hole_centres, 0, ref_hole_offset_z - rpi_v_hole_centres]) fixhole();
        translate([ref_hole_offset_x, 0, ref_hole_offset_z - rpi_v_hole_centres]) fixhole();
        //usb
        translate([ref_hole_offset_x + usb_h_hole_centres, 0, ref_hole_offset_z]) fixhole();
        translate([ref_hole_offset_x + usb_h_hole_centres, 0, ref_hole_offset_z - usb_v_hole_centres]) fixhole();
        translate([ref_hole_offset_x, 0, ref_hole_offset_z - usb_v_hole_centres]) fixhole();
        
        //shaft hole
        translate([-2*wheel_thickness/3, 0, eff_wheel_radius]) rotate([0, 90, 0]) cylinder(h=3*wheel_thickness/2, d=interference_bore, $fn=32, center=true);
        //gap for connector
        translate([cx_offset, recess, cz_offset - con_gap_dim]) cube([con_gap_dim * 1.75, con_gap_dim, con_gap_dim], center=true);
    }
}
module yew(internal_width, depth, clearance, wall_thickness) {
    //make a U shape bracket centred on shaft axis, with clearance
    walls = 2*wall_thickness;
    difference() {
        union() {
            //draw shaft axis for reference
            //side bearings
            translate([(internal_width + wall_thickness)/2, 0, 0]) rotate([0,90,0]) cylinder(h=wall_thickness, d=depth, $fn=32, center=true);
            translate([-(internal_width + wall_thickness)/2, 0, 0]) rotate([0,90,0]) cylinder(h=wall_thickness, d=depth, $fn=32, center=true);
            //side bases
            translate([(internal_width + wall_thickness)/2, 0, -clearance/2]) cube([wall_thickness, depth, clearance], center=true);
            translate([-(internal_width + wall_thickness)/2, 0, -clearance/2]) cube([wall_thickness, depth, clearance], center=true);
            //base
            translate([0, 0, -(clearance+wall_thickness/2)]) cube([internal_width+walls, depth, wall_thickness], center=true);
        }
    }   
}
module bracket() {
    //wide U section
    difference() {
        union() {
            yew(bkt_width, bkt_depth, bkt_height, bkt_wall_thickness);
            //enlarged foot
            hull() {
                translate([(bkt_width-bkt_wall_thickness)/2, -bkt_depth/2, -(bkt_height + bkt_wall_thickness/2)]) cylinder(h=bkt_wall_thickness, d=6, $fn=32, center=true);
                translate([-(bkt_width-bkt_wall_thickness)/2, -bkt_depth/2, -(bkt_height + bkt_wall_thickness/2)]) cylinder(h=bkt_wall_thickness, d=6, $fn=32, center=true);
                translate([bkt_width/3, -bkt_depth, -(bkt_height + bkt_wall_thickness/2)]) cylinder(h=bkt_wall_thickness, d=6, $fn=32, center=true);
                translate([-bkt_width/3, -bkt_depth, -(bkt_height + bkt_wall_thickness/2)]) cylinder(h=bkt_wall_thickness, d=6, $fn=32, center=true);
            }
        }//end union
        //rhs spigot clearance hole
        translate([bkt_width/2 + 1, 0, 0]) rotate([0,90,0]) cylinder(h=bkt_wall_thickness + 2, d=clearance_bore, $fn=32, center=true);
        //lhs glue-in spigot clearance hole
        translate([-bkt_width/2, 0, 0]) rotate([0,90,0]) cylinder(h=(bkt_wall_thickness + plate_bkt_gap)+1, d=clearance_bore, $fn=32, center=true);
        //fixing slot
        hull() {
            translate([0, -5, -(bkt_height + bkt_wall_thickness/2)]) cylinder(h=bkt_wall_thickness+1, d=fix_hole_dia, $fn=32, center=true);
            translate([0, -15, -(bkt_height + bkt_wall_thickness/2)]) cylinder(h=bkt_wall_thickness+1, d=fix_hole_dia, $fn=32, center=true);
        }
    }
    
    //narrow U section
    translate([-(plate_width-wheel_thickness)/2,0,-(eff_wheel_radius+eff_worm_radius)]) rotate([0, 0, 90]) difference() {
        yew(bkt_depth, bkt_depth, bkt_height-(eff_wheel_radius+eff_worm_radius), bkt_wall_thickness);
        //rear glue-in spigot clearance hole
        translate([bkt_depth/2+1, 0, 0]) rotate([0, 90, 0]) cylinder(h=bkt_wall_thickness + 2, d=clearance_bore, $fn=32, center=true);
        //front spigot clearance hole
        translate([-bkt_depth/2-1, 0, 0]) rotate([0, 90, 0]) cylinder(h=bkt_wall_thickness + 2, d=clearance_bore, $fn=32, center=true);
        //access slot so worm can be dropped in
        translate([-bkt_depth/2-1, 0, clearance_bore]) rotate([0, 90, 0]) cube([clearance_bore*2, clearance_bore, bkt_wall_thickness * 2], $fn=32, center=true);
    }

}
module worm() {
    difference() {
        union() {
            //the worm itself
            rotate([0, 90, 0]) import("shared/worm-wheel-worm.stl", convexity=10);
            //round shoulder that sits in bracket
            translate([0, -worm_length/2, -eff_worm_radius]) rotate([90, 0, 0]) cylinder(h=shoulder_length, d=interference_bore, $fn=32);
            //hex shoulder that sits on end
            translate([0, -((worm_length/2)+(shoulder_length)), -eff_worm_radius]) rotate([90, 0, 0]) cylinder(h=shoulder_length*2, d1=hex_hole_dia+0.5, d2=hex_hole_dia-0.5, $fn=6);
        }
    //enlarged glue-in spigot hole
    translate([0, worm_length/2, -eff_worm_radius]) rotate([90, 0, 0]) cylinder(h=worm_length/2, d=interference_bore, $fn=32);
    }
}
module assembly() {
    rotate([0, 0, 180]) {
        %translate([0, -17, 5]) color("grey", alpha=0.25) case();
        translate([-19.5, 0, 5]) rotate([90, 0, 0]) union() {
            mount();
            translate([ref_hole_offset_x, 0, ref_hole_offset_z]) union() {
                *color("red") translate([0, recess - (plate_thickness + bush_height + 0.05), 0]) usb_camera();
                color("blue") translate([0, recess - (plate_thickness + bush_height + 0.05), 0]) rpi_camera();
            }
            translate([-38, 8, 45]) rotate([-90, 0, 0]) rpi_zero();
            *color("orange") translate([-38, 8, 45]) rotate([-90, 0, 0]) rpi_clip();
            color("grey") translate([(plate_width-wheel_thickness)/2, 0, eff_wheel_radius]) bracket();
            worm();
        }
    }
}

//parts & assembly
*rpi_zero();
*rotate([0, 90, 0]) rpi_clip(true);
assembly();

//uncomment each line to generate stl for each printed part
*translate([25, 20, wheel_thickness/2]) rotate([0, 270, 0]) mount();//with raft
*rotate([270, 0, 0]) worm();//with raft
*translate([0, 0, bkt_height+bkt_wall_thickness]) bracket();
