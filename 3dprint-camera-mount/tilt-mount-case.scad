/*
    Tilt Mount Project Case
    
    Based on 158 x 90 x 60 mm Waterproof Junction Project Box
    
*/

use <shared/Chamfer-Fillet-Machine.scad>

case_width = 90;//mm
case_length = 158;//mm
case_thickness = 2.6;//mm
case_corner_dia = 6;//mm
hor_hole_spacing = 78;
ver_hole_spacing = 146;

lid_depth = 15;//mm increase this if you need deeper lids to accomodate longer lenses
hole_dia = 4.5;//mm
recess_dia = 7.5;//mm
csk_depth = 6.0;//mm
retainer_height = 1;//mm
pane_thickness = 1.2;//mm CD Case Lid
pane_width = 75;//mm actual size of acrylic pane
pane_length = 100;//mm actual size of acrylic pane
pane_rail_dim = 10;//mm

base_depth = 45;//mm increase this if you need deeper base
threaded_insert_dia = 5.6;//mm adjust for specific inserts/self tapping/etc. 
threaded_insert_depth = 6;//mm

//these parameters are chosen so lid mates with purchased base 
gnm_width = (hor_hole_spacing/2) + 5;
gnm_height = (ver_hole_spacing/2) + 5;
gnm_cutout_width = 9.3;
gnm_cutout_height = 9.3;
gnm_minor_rad = 3.0;
gnm_major_rad = 4.35;
gnm_chan_dim = 1.8;//suits a gasket made from TPU filament, 2.0mm for supplied case gasket
gnm_ridge_dim = 1.0;

case_tilt_mount_hole_dia = 4.5;//mm
case_fix_hole_dia = 6;//mm
case_cable_hole_dia = 12.5;//mm
wall_hole_offset_y = 5 * case_length / 16;

module gasket_quadrant(
    gq_width,
    gq_height,
    gq_cutout_width, 
    gq_cutout_height, 
    gq_minor_rad, 
    gq_major_rad,
    gq_chan_dim
) {
    pts1 = gnomon(
        gq_width,
        gq_height,
        gq_cutout_width,
        gq_cutout_height,
        gq_minor_rad, 
        gq_major_rad
    );
    pts2 = gnomon(
        gq_width - gq_chan_dim,
        gq_height - gq_chan_dim,
        gq_cutout_width,
        gq_cutout_height,
        gq_minor_rad - gq_chan_dim, 
        gq_major_rad + gq_chan_dim
    );
    linear_extrude(gq_chan_dim) difference() {
        chamfer_fillet_2d(pts1);
        chamfer_fillet_2d(pts2);
    }
}
module gasket(
    gq_width,
    gq_height,
    gq_cutout_width, 
    gq_cutout_height, 
    gq_minor_rad, 
    gq_major_rad,
    gq_chan_dim
) {
    gasket_quadrant(
        gq_width,
        gq_height,
        gq_cutout_width, 
        gq_cutout_height, 
        gq_minor_rad, 
        gq_major_rad,
        gq_chan_dim
    );
    mirror([1, 0, 0]) gasket_quadrant(
        gq_width,
        gq_height,
        gq_cutout_width, 
        gq_cutout_height, 
        gq_minor_rad, 
        gq_major_rad,
        gq_chan_dim
    );
    mirror([0, 1, 0]) gasket_quadrant(
        gq_width,
        gq_height,
        gq_cutout_width, 
        gq_cutout_height, 
        gq_minor_rad, 
        gq_major_rad,
        gq_chan_dim
    );
    rotate([0, 0, 180]) gasket_quadrant(
        gq_width,
        gq_height,
        gq_cutout_width, 
        gq_cutout_height, 
        gq_minor_rad, 
        gq_major_rad,
        gq_chan_dim
    );
}
module recess_gnomon(sink) {
    lid_quad_recess_pts = gnomon(
        ((hor_hole_spacing + hole_dia)/2), 
        (ver_hole_spacing + hole_dia)/2, 
        gnm_cutout_width, 
        gnm_cutout_height, 
        gnm_minor_rad - 2.75, 
        gnm_major_rad + 2.75
    );
    translate([0.01, 0.01, case_thickness + 0.1]) linear_extrude(sink) chamfer_fillet_2d(lid_quad_recess_pts);
}
module fix_hole() {
    //countersink
    csk_height = recess_dia - hole_dia;//for 45 degree countersink
    translate([0, 0, lid_depth - csk_depth]) cylinder(h=csk_height, d1=recess_dia, d2=hole_dia, $fn=32, center=true);
    //hole
    cylinder(h=lid_depth*3, d=hole_dia, $fn=32, center=true);
    //counterbore
    cbr_height = lid_depth - (csk_depth + csk_height - retainer_height);
    translate([0, 0, lid_depth - ((cbr_height + csk_height)/2 + csk_depth)]) cylinder(h=cbr_height, d=recess_dia, $fn=32, center=true);
    //screw retainer - as lid is fitted upside down!
    translate([0, 0, (retainer_height/2) - 0.05]) scale([0.875, 1.0, 1.0]) cylinder(h=retainer_height, d=recess_dia, $fn=32, center=true);    
}
module insert_hole() {
    //hole
    cylinder(h=threaded_insert_depth, d=threaded_insert_dia, $fn=32, center=true);
}
module lid() {
    lid_points = [
        [-case_width/2, -case_length/2, case_corner_dia],
        [-case_width/2, case_length/2, case_corner_dia],
        [case_width/2, case_length/2, case_corner_dia],
        [case_width/2, -case_length/2, case_corner_dia]
    ];
    difference() {
        //outer shell
        linear_extrude(lid_depth) chamfer_fillet_2d(lid_points);
        //recesses
        lid_sink = lid_depth - case_thickness;
        recess_gnomon(lid_sink);
        mirror([1, 0, 0]) recess_gnomon(lid_sink);
        mirror([0, 1, 0]) recess_gnomon(lid_sink);
        rotate([0, 0, 180]) recess_gnomon(lid_sink);
        //gasket slot
        translate([0, 0, lid_depth - gnm_chan_dim + 0.1]) gasket(
            gnm_width,
            gnm_height,
            gnm_cutout_width,
            gnm_cutout_height,
            gnm_minor_rad, 
            gnm_major_rad,
            gnm_chan_dim
        );
        //fixing holes
        translate([-hor_hole_spacing/2, -ver_hole_spacing/2, 0]) fix_hole();
        translate([-hor_hole_spacing/2, ver_hole_spacing/2, 0]) fix_hole();
        translate([hor_hole_spacing/2, -ver_hole_spacing/2, 0]) fix_hole();
        translate([hor_hole_spacing/2, ver_hole_spacing/2, 0]) fix_hole();
        //transparent window opening
        win_width = (pane_width/2) - pane_rail_dim;
        win_length = (pane_length/2) - pane_rail_dim;
        translate([0, 0, -0.1]) linear_extrude(lid_depth) chamfer_fillet_2d([
            [-win_width, -win_length, case_corner_dia],
            [-win_width, win_length, case_corner_dia],
            [win_width, win_length, case_corner_dia],
            [win_width, -win_length, case_corner_dia]
        ]);
        //transparent window recess
        translate([0, 0, (lid_depth/2) + pane_thickness]) cube([pane_width, pane_length, lid_depth], center=true);
    }
}
module base() {
    base_points = [
        [-case_width/2, -case_length/2, case_corner_dia],
        [-case_width/2, case_length/2, case_corner_dia],
        [case_width/2, case_length/2, case_corner_dia],
        [case_width/2, -case_length/2, case_corner_dia]
    ];
    difference() {
        union() {
            //outer shell
            linear_extrude(base_depth) chamfer_fillet_2d(base_points);
            //gasket ridge
            translate([0, 0, base_depth]) gasket(
                gnm_width - (gnm_chan_dim - gnm_ridge_dim)/2,
                gnm_height - (gnm_chan_dim - gnm_ridge_dim)/2,
                gnm_cutout_width,
                gnm_cutout_height,
                gnm_minor_rad, 
                gnm_major_rad,
                gnm_ridge_dim
            );
        }
        //recesses
        base_sink = base_depth - case_thickness;
        translate([0, 0, 0]) union() {
            recess_gnomon(base_sink);
            mirror([1, 0, 0]) recess_gnomon(base_sink);
            mirror([0, 1, 0]) recess_gnomon(base_sink);
            rotate([0, 0, 180]) recess_gnomon(base_sink);
        }
        //threaded insert holes
        offset_x = hor_hole_spacing/2;
        offset_y = ver_hole_spacing/2;
        offset_z = base_depth - (threaded_insert_depth/2) + 0.1;
        translate([-offset_x, -offset_y, offset_z]) insert_hole();
        translate([-offset_x, offset_y, offset_z]) insert_hole();
        translate([offset_x, -offset_y, offset_z]) insert_hole();
        translate([offset_x, offset_y, offset_z]) insert_hole();
        //central tilt mount mounting slot
        hull() {
            translate([(case_width-case_thickness)/2, 0, base_depth/3]) rotate([0, 90, 0]) cylinder(h=case_thickness*3, d=case_tilt_mount_hole_dia, $fn=32, center=true);
            translate([(case_width-case_thickness)/2, 0, 2*base_depth/3]) rotate([0, 90, 0]) cylinder(h=case_thickness*2, d=case_tilt_mount_hole_dia, $fn=32, center=true);
        }
        //offset case mounting screw slot
        hull() {
            translate([(case_thickness-case_width)/2, -wall_hole_offset_y, base_depth/2]) rotate([0, 90, 0]) cylinder(h=case_thickness*3, d=case_fix_hole_dia, $fn=32, center=true);
            translate([(case_thickness-case_width)/2, -wall_hole_offset_y, base_depth*2]) rotate([0, 90, 0]) cylinder(h=case_thickness*2, d=case_fix_hole_dia, $fn=32, center=true);
        }
        //offset cable entry
        translate([(case_thickness-case_width)/2, wall_hole_offset_y, base_depth/2]) rotate([0, 90, 0]) cylinder(h=case_thickness*3, d=case_cable_hole_dia, $fn=32, center=true);
    }
}
function gnomon(
    width,
    height,
    cutout_width, 
    cutout_height, 
    minor_rad, 
    major_rad
)
     = [
        //x, y, r
        [-width + cutout_width, -height, minor_rad],
        [-width + cutout_width, -height + cutout_height, major_rad],
        [-width, -height + cutout_height, minor_rad],
        [-width, 0, 0],
        [0, 0, 0],
        [0, -height, 0]
    ];

module lid_end_test() {
    intersection() {
        lid();
        translate([0, -ver_hole_spacing/2]) cube([100, 20, 50], center=true);
    }
}
*lid_end_test();//economic sample for checking dimensions
translate([100, 0, 0]) lid();
base();
