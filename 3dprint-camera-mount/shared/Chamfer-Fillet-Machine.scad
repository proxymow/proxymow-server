//Chamfer Fillet Machine

//find coordinates in triplets
function coords(pts) = [
    for(t=[0: len(pts)-1]) [is_num(pts[t][0]) ? pts[t][0] : 0, is_num(pts[t][1]) ? pts[t][1] : 0]
];

//find wrapping index 
function iwrap(pts, i) = i < 0 ? len(pts)-1 : i % len(pts);

//find triplet of points, i-1, i, i+1
function triplet(pts, i) = [
    pts[iwrap(pts, i - 1)], 
    pts[iwrap(pts, i)], 
    pts[iwrap(pts, i + 1)]
];

//find intersection angle of 2 lines i-1..i, i..i+1
function intersect_angle(pts, i) = 
    let(
        tplt = triplet(pts, i),
        x1 = tplt[0][0],
        y1 = tplt[0][1],
        x = tplt[1][0],
        y = tplt[1][1],
        x2 = tplt[2][0],
        y2 = tplt[2][1],
        
        vA = [x - x1, y - y1],
        vB = [x - x2, y - y2],
        
        AcrossB = cross(vA, vB),
        AdotB = vA * vB,
        
        theta = atan2(AcrossB, AdotB)
    )
    theta;
    
//find vector same direction different magnitude
function get_vector(pts, i) = 
    let(
        tplt = triplet(pts, i),
        x1 = tplt[0][0],
        y1 = tplt[0][1],
        x = tplt[1][0],
        y = tplt[1][1],
        V = [x1 - x, y1 - y]
    )
    V;
    
//find vector same direction different magnitude
function extend_vect(V, m) = 
    let(
        mag = sqrt(V[0]^2 + V[1]^2),
        scale_factor = m / mag,
        EV = V * scale_factor
    )
    EV;
    
//find vector same direction different magnitude
function extend_vector(pts, i, mag) = 
    let(
        V = get_vector(pts, i),
        EV = extend_vect(V, mag)
    )
    EV;
    
//rotate vector
//(x′,y′)=(xcosθ−ysinθ,xsinθ+ycosθ)
function rotate_vector(V, alpha) =
    let(
        xr = V[0] * cos(alpha) - V[1] * sin(alpha),
        yr = V[0] * sin(alpha) + V[1] * cos(alpha)
    ) [xr, yr];
    
function vector_magnitude(V) = sqrt(V[0]^2 + V[1]^2);
function vector_angle(V) = atan2(V[1], V[0]);
function sum(v) = [for(p=v) 1]*v;
    
function tangent_centres(pts) = [ 
    for (i=[0: len(pts) - 1]) 
        let(
            //intersection angle +ve for internal corners (fillets) -ve for external corners (chamfers)
            theta = intersect_angle(pts, i),
            alpha = theta/2,
            mode = (theta > 0) ? "chamfer" : "fillet",
            qa = (theta == 0 ? 0 : pts[i][2] / sin(alpha)),
            QAD = (theta == 0 ? [0, 0] : extend_vector(pts, i, qa)),
            QA = (theta == 0 ? [0.1, 0.1] : rotate_vector(QAD, alpha)),
            //echo("QA", QA, "QAD", QAD, "qa", qa, "alpha", alpha),
            x = pts[i][0] + QA[0],
            y = pts[i][1] + QA[1]
        ) [x, y] 
];
    
module vector_line(V, x=0, y=0, line_thickness=0.05) {
    translate([x, y, 0]) {
        //line
        hull() {
            circle(d=line_thickness, $fn=32);
            translate([V[0], V[1], 0]) circle(d=line_thickness, $fn=32);
        }
    }
}    
module vector_arrow(V, x=0, y=0, line_thickness=0.05) {
    translate([x, y, 0]) {
        //line
        hull() {
            circle(d=line_thickness, $fn=32);
            translate([V[0], V[1], 0]) circle(d=line_thickness, $fn=32);
        }
        //arrowhead
        dir_angle = atan2(V[1], V[0]);
        arr_size = line_thickness*5;
        translate([-arr_size * cos(dir_angle), -arr_size * sin(dir_angle)]) translate([V[0], V[1], 0]) rotate([0, 0, dir_angle]) circle(line_thickness*5, $fn=3);
    }
}
module points_list_diagram(pts, xscaling = 10, yscaling = 4, font_size = 4) {
    //Draw and Label a list of x,y points
    for (i=[0:len(pts)-1]) {
        echo("i: ", i, pts[i]);
        label = str(i, ":", round(pts[i][0]), ",", round(pts[i][1]));
        color("black") translate([xscaling * pts[i][0], yscaling * pts[i][1], 0]) text(label, font_size);
    }
    %scale([xscaling, yscaling, 1.0]) polygon(pts);    
}

//converts a list of points into filleted chamfered 2D Polygon
module chamfer_fillet_debug(pts, debug=true) {
    ppts = [ for (i=[0:len(pts)-1]) [pts[i][0], pts[i][1]] ];
    if (debug) echo("ppts: ", ppts);
    //polygon(ppts);

    //label points
    centroid = (max(pts) + min(pts)) / 2;
    echo("centroid: ", centroid);
    translate(centroid) scale([1.5, 1.5, 1.0]) translate(-centroid) for (i=[0: len(pts) - 1]) {
        color("black") translate([pts[i][0], pts[i][1], 0]) {
            difference() {
                circle(0.25, $fn=32);
                circle(0.20, $fn=32);
            }
            translate([-0.1, -0.1, 0]) text(str(i, "   r", pts[i][2]), size=0.2);
        }
    }

    //calculations for a chamfered filleted polygon from (x, y, r) points
    for (i=[0: len(pts) - 1]) {

        //intersection angle +ve for internal corners (fillets) -ve for external corners (chamfers)
        theta = intersect_angle(pts, i);
        alpha = theta/2;
        if (debug) echo("i: ", i, "intersect angle theta: ", theta, "bisect angle: ", alpha);
        if (theta != 0 && pts[i][2] > 0) {
            
            mode = (theta > 0) ? "Chamfer" : "Fillet";
            echo("Mode: ", mode);
            
            //distance to tangent circle centre
            qa = pts[i][2] / sin(alpha);
            if (debug) echo("\ti: ", i, "distance to tangent circle centre [qa]: ", qa);
            
            //distance to tangent touchpoint
            //qa^2 = r^2 + qb^2
            qb = sqrt(qa^2 - pts[i][2]^2);
            if (debug) echo("\tdistance to tangent touchpoint [qb]: ", qb);

            QBD = extend_vector(pts, i, abs(qb));
            if (debug) echo("\ti: ", i, "extended_vector: ", QBD);
            
            //highlight vector
            if (debug) color("blue") vector_arrow(QBD, pts[i][0], pts[i][1]);
            
            //rotate vector
            QB = rotate_vector(QBD, theta);
            if (debug) echo("\ti: ", i, "rotated vector: ", QB);

            //highlight rotated vector
            if (debug) color("red") vector_arrow(QB, pts[i][0], pts[i][1]);

            //construct triangular polygon
            color("white", 0.5) polygon([
                [pts[i][0], pts[i][1]],
                [pts[i][0] + QB[0], pts[i][1] + QB[1]],
                [pts[i][0] + QBD[0], pts[i][1] + QBD[1]],
                [pts[i][0], pts[i][1]]
            ]);

            QAD = extend_vector(pts, i, abs(qa));
            if (debug) echo("\ti: ", i, "pre-bisector vector: ", QAD);
            QA = rotate_vector(QAD, alpha);
            if (debug) echo("\ti: ", i, "QA: ", QA);
            
            //highlight bisector vector
            %if (debug) color("yellow") vector_arrow(QA, pts[i][0], pts[i][1]);
                
            //highlight tangential circle
            color("teal", 0.5) translate([pts[i][0] + QA[0], pts[i][1] + QA[1], 0]) circle(pts[i][2], $fn=32);
            
        } else {
            echo(str("Intersect Angle Zero! Ignoring Point: ", i)); 
        }
    }
}
//chamfer fillet components
module chamfer_fillet_triangles(pts, filter="none") {
    for (i=[0: len(pts) - 1]) {
        //intersection angle +ve for internal corners (fillets) -ve for external corners (chamfers)
        theta = intersect_angle(pts, i);
        alpha = theta/2;
        mode = (theta > 0) ? "chamfer" : "fillet";

        if (theta != 0 && pts[i][2] > 0 && mode == filter){

            //distance to tangent circle centre
            qa = pts[i][2] / sin(alpha);
            
            //distance to tangent touchpoint
            //qa^2 = r^2 + qb^2
            qb = sqrt(qa^2 - pts[i][2]^2);

            QBD = extend_vector(pts, i, abs(qb));
            //rotate vector
            QB = rotate_vector(QBD, theta);
            //construct triangular polygon
            polygon([
                [pts[i][0], pts[i][1]],
                [pts[i][0] + QB[0], pts[i][1] + QB[1]],
                [pts[i][0] + QBD[0], pts[i][1] + QBD[1]],
                [pts[i][0], pts[i][1]]
            ]);
        }//end if
    }//next
}
module chamfer_fillet_circles(pts, filter="none") {
    for (i=[0: len(pts) - 1]) {
        //intersection angle +ve for internal corners (fillets) -ve for external corners (chamfers)
        theta = intersect_angle(pts, i);
        alpha = theta/2;
        mode = (theta > 0) ? "chamfer" : "fillet";

        if (theta != 0 && pts[i][2] > 0 && mode == filter) {

            //distance to tangent circle centre
            qa = pts[i][2] / sin(alpha);
            QAD = extend_vector(pts, i, abs(qa));
            QA = rotate_vector(QAD, alpha);

            //construct tangential circle
            translate([pts[i][0] + QA[0], pts[i][1] + QA[1], 0]) circle(pts[i][2], $fn=32);
            
        }//end if
    }//next
}
module chamfer_fillet_2d(pts) {
    //create a chamfered filleted polygon from (x, y, r) points

    //convert point triplets to x,y pairs for polygon
    ppts = [ for (i=[0:len(pts)-1]) [pts[i][0], pts[i][1]] ];
    difference() {
        union() {
            difference() {
                polygon(ppts);
                
                //stage 1 remove chamfer triangles
                chamfer_fillet_triangles(pts, "chamfer");
            }
            //stage 2 add chamfer circles and fillet triangles
            chamfer_fillet_circles(pts, "chamfer");
            chamfer_fillet_triangles(pts, "fillet");
        }    
        //stage 3 remove fillet circles
        chamfer_fillet_circles(pts, "fillet");
    }
}
module chamfer_fillet_3d(pts, width, incl_cap_1=true, incl_cap_2=true) {
    //create a extruded chamfered filleted polygon from (x, y, r) points
    linear_extrude(width) chamfer_fillet_2d(pts);

    //use mean of non-zero radii
    radii = [ for (i=[0: len(pts) - 1]) pts[i][2]];
    r = sum(radii)/len(pts);
        
    if (incl_cap_1) {
        endcap_wireframe(pts);
        translate([0, 0, -r]) linear_extrude(width) polygon(coords(tangent_centres(pts)));
        //polygon(tangent_centres(pts));
    }
    if (incl_cap_2) {
        translate([0, 0, width]) {
            endcap_wireframe(pts);
            linear_extrude(r) polygon(coords(tangent_centres(pts)));
        }
    }    
}

module endcap_wireframe(pts) {
    //place hemispheres at each internal tangent
    //use mean of non-zero radii
    ar = sum([ for (i=[0: len(pts) - 1]) pts[i][2]])/len(pts);
    echo("aggregate r:", ar);
    tcs = tangent_centres(pts);
    echo("tangent_centres: ", tcs);
    
    for (i=[0: len(pts) - 1]) {

        //sequential pair index
        j = (i + 1) % len(pts);
        
        //requested radius
        r = pts[i][2];
        rj = pts[j][2];
        echo (r, rj, tcs[i], tcs[j]);
        
        hull() {
                //construct first tangential sphere?
                if (is_num(tcs[i][0])) {
                    translate([tcs[i][0], tcs[i][1], 0]) resize([2*r, 2*r, 2*ar]) sphere(r, $fn=32);
                }
                
                //construct second tangential sphere
                if (is_num(tcs[j][0])) {
                    translate([tcs[j][0], tcs[j][1], 0]) resize([2*rj, 2*rj, 2*ar]) sphere(rj, $fn=32);
                }
                
        }//end hull
    }//next
}//end module