import sys
from math import cos, sin, atan, tan, acos, pi
from build123d import *
from ocp_vscode import *

width= 3.1 * M
back_width = 2.9 * M
back_inset = (width - back_width)/2
height = 2 * M
depth = 1 * M
drop = 0.2 * M
back_foot_angle = 40

front_offset = 0.5 * M
back_offset = 0.3 * M
tube_od = 40 * MM
wall_thickness = 2 * MM
tube_id = tube_od - wall_thickness * 2
cross_member_od = 25 * MM
cross_member_id = cross_member_od - wall_thickness * 2
bend_radius = 5 * tube_od
# The front legs rise x-plumb (parallel to the Z axis when viewed from ahead)
# from the deck up to leg_bend_height, then lean inboard toward the top corner.
# The knee point keeps the continuous aft rake (dy/dz = front_offset/height),
# so the side view is unchanged.  The plumb lower run lines the legs up with
# the boat's existing (unmodelled) stern rails.  Keep this well below the
# top-corner fillet zone (~1.8 m) for this geometry.
leg_bend_height = 0.8 * M
rise_rate = 0
top_support_offset = 0.25 * M
side_support_offset = 0.1 * M
brace_offset = 0.5 * M

side_support_adjustment = (back_inset/height) * 250

# --- Crude sailboat stern context (visualization only, not exported) ----
# The front arch feet (flat plates, bottom at z=0) sit on a horizontal deck
# while the back feet (tilted by back_foot_angle, bottom at z=-drop) sit on
# the sloping transom/scoop.  The hull widths below are sized so the 3.1 m
# arch comes close to the hull edge (≈30 mm margin at the front feet).
boat_cx = width/2              # boat centreline (deck symmetric about it)
deck_width_aft = 3.0 * M       # hull width at the aft end (y = hull_aft_end)
deck_width_fwd = 3.4 * M       # hull width at the forward cut
hull_aft_end = 1.3 * M         # hull aft extent (below the scoop surface)
hull_len_aft = 1.5 * M         # modeled length forward of the transom crease
hull_bottom_z = -1.0 * M       # flat-bottom depth
show_boat = True               # build & show the context hull beside the arch

# --- Mass estimation -----------------------------------------------------
STEEL_DENSITY = 8.0  # g/cm³ — 316 stainless steel (≈8,000 kg/m³)

def volume_mass(volume_mm3: float, density_g_cm3: float = STEEL_DENSITY) -> float:
    """Mass in kg of a volume given in mm³ at a density given in g/cm³.

    mm³ → cm³ is ÷1e3, then g → kg is ÷1e3, so kg = mm³ × g/cm³ / 1e6.
    """
    return volume_mm3 * density_g_cm3 / 1e6

def part_mass(part: Part, density_g_cm3: float = STEEL_DENSITY) -> float:
    """Estimate the mass of a part in kg (build123d volumes are in mm³)."""
    return volume_mass(part.volume, density_g_cm3)

def front_tail(corner_x):
    """Path points after the front top corner: the flat-top centre point, or
    the rise_rate crown point."""
    if rise_rate:
        return [(corner_x + bend_radius,
                 front_offset + front_offset/height * bend_radius * rise_rate,
                 height + bend_radius * rise_rate)]
    return [(corner_x, front_offset, height),
            (width/2, front_offset, height)]

# The front leg path gains a knee at leg_bend_height: the lower run is pinned
# to the foot's x (plumb when viewed from ahead) while y keeps raking aft at
# the continuous rate front_offset/height, so the side view is unchanged.
knee_y = front_offset / height * leg_bend_height

# Keep the visible straight top span exactly where it is: the top-corner
# vertex itself is trimmed away by the R200 corner fillet, so its x is nudged
# (fixed-point) until the fillet tangency on the horizontal run matches the
# pre-knee corner direction — the knee would otherwise move the tangency
# ~6 mm inboard and shrink the span.
corner_dir = Vector(back_inset, front_offset, height).normalized()
span_tangent_x = back_inset + bend_radius * tan(acos(corner_dir.dot(Vector(1, 0, 0)))/2)
corner_x = back_inset
if not rise_rate:   # flat top: keep the straight span where it was
    for _ in range(3):
        probe_pts = [(0, 0, 0), (0, knee_y, leg_bend_height)] + front_tail(corner_x)
        with BuildLine() as probe_line:
            FilletPolyline(probe_pts, radius=bend_radius)
        probe_span = next((e for e in probe_line.edges()
                           if abs(e.start_point().Z - e.end_point().Z) < 1e-6
                           and e.length > M), None)
        if probe_span is None:
            break
        corner_x += span_tangent_x - probe_span.start_point().X
        if abs(span_tangent_x - probe_span.start_point().X) < 0.05:
            break

points = [(0, 0, 0), (0, knee_y, leg_bend_height)] + front_tail(corner_x)
if rise_rate:
    point2 = (width - points[-1][0], points[-1][1], points[-1][2])

back_points = [(back_inset,depth,-drop),
               (back_inset,depth + back_offset,height),
               (back_inset+bend_radius,depth + back_offset+ back_offset/height* bend_radius*rise_rate,height+bend_radius*rise_rate)]
if rise_rate:
    back_point2 = (width - back_points[-1][0], back_points[-1][1], back_points[-1][2])
else:
    back_points[2] = (width/2, back_points[-1][1], back_points[-1][2])


class ArchFoot(BasePartObject):
    def __init__(
        self,
        thickness: float = 8,
        diameter: float = 100,
        hole_diameter: float = 30,
        bolt_count: int = 3,
        bolt_hole_diameter: float = 8.5,
        bolt_hole_offset: float = 25,
        rotation: RotationLike = (0, 0, 90),
        align: tuple[Align, Align, Align] = (Align.CENTER, Align.CENTER, Align.MIN),
        mode: Mode = Mode.ADD,
    ):
    
        with BuildPart() as foot:
            Cylinder(radius=diameter/2, height=thickness)
            Hole(radius=hole_diameter/2,depth=thickness)
            if bolt_count:
                with PolarLocations(radius=(diameter-bolt_hole_offset)/2,count=bolt_count):
                    Hole(radius=bolt_hole_diameter/2,depth=thickness)
        super().__init__(part=foot.part, rotation=rotation, align=align, mode=mode)

class Padeye(BasePartObject):
    def __init__(
        self,
        size: float = 6,
        diameter: float = 25,
        rotation: RotationLike = (0, 0, 0),
        align: tuple[Align, Align, Align] = (Align.CENTER, Align.MIN, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
    
        with BuildPart() as padeye:
            Torus(major_radius=diameter/2, minor_radius=size/2,major_angle=180,
                  rotation=rotation, align=align, mode=mode)
        super().__init__(part=padeye.part, rotation=rotation, align=align, mode=mode)


with BuildPart() as arch:
    with BuildLine() as frame:
        l1 = FilletPolyline(points, radius=bend_radius)
        if rise_rate:
            ta = TangentArc((points[-1],point2),tangent=l1.tangent_at(1),mode=Mode.PRIVATE).trim(0,0.5)
            add(ta)
    with BuildSketch(Plane(origin=l1 @ 0, z_dir=l1 % 0)) as tube:
        Circle(tube_od/2)
        Circle(tube_id/2,mode=Mode.SUBTRACT)
    sweep(path=frame)
    af = ArchFoot(mode=Mode.PRIVATE)
    front_foot_volume = af.volume  # capture before fusing into the frame
    tf = af.faces().sort_by(Axis.Z)[-1]  
    split(bisect_by=tf)
    add(af)

with BuildPart() as arch2:
    with BuildLine() as back_frame:
        l1 = FilletPolyline([(back_inset,depth - back_offset,-drop - (drop + height))] +back_points[1:], radius=bend_radius)
        if rise_rate:
            ta = TangentArc((back_points[-1],back_point2),tangent=l1.tangent_at(1),mode=Mode.PRIVATE).trim(0,0.5)
            add(ta)
    with BuildSketch(Plane(origin=l1 @ 0, z_dir=l1 % 0)) as back_tube:
        Circle(tube_od/2)
        Circle(tube_id/2,mode=Mode.SUBTRACT)
    sweep(path=back_frame)
    with Locations(back_points[0]):
        af = ArchFoot(rotation=(-back_foot_angle,0,90),mode=Mode.PRIVATE)
    back_foot_volume = af.volume  # capture before fusing into the frame
    back_foot_af = af  # kept so the boat hull can be built on its contact plane
    tf = af.faces().sort_by(Axis.Z)[-4]  
    split(bisect_by=tf)
    add(af)
    add(arch.part)
    


    p1 = frame.line.edges().sort_by(Axis.Z)[-1].position_at(top_support_offset,position_mode=PositionMode.LENGTH)
    p2 = back_frame.line.edges().sort_by(Axis.Z)[-1].position_at(top_support_offset,position_mode=PositionMode.LENGTH)
    l1 = Line([p1,p2])
    with BuildSketch(Plane(origin=l1 @ 0, z_dir=l1 % 0)) as top_support:
        Circle(cross_member_od/2)
        Circle(cross_member_id/2,mode=Mode.SUBTRACT)
    sweep(path=l1)


    # Front side-rail anchors.  The knee splits the front leg's lowest straight
    # edge (it now ends at ~0.8 m), so anchor on the leg's *upper* straight run
    # to keep the rails at their established height just below the top corner.
    front_rail_edge = max(
        (e for e in frame.line.edges()
         if e.geom_type is GeomType.LINE
         and abs((e.end_point() - e.start_point()).Z / e.length) > 0.3
         and e.length > 0.2*M),
        key=lambda e: min(e.start_point().Z, e.end_point().Z))
    with BuildLine() as side_support_frame:
        p1 = front_rail_edge.position_at(front_rail_edge.length
                                         - side_support_offset - side_support_adjustment,
                                         position_mode=PositionMode.LENGTH)
        a2 = back_frame.line.edges().sort_by(Axis.Z)[0]
        p2 = a2.position_at(a2.length - side_support_offset,position_mode=PositionMode.LENGTH)
        l1 = Line([p1,p2])
    with BuildSketch(Plane(origin=l1 @ 0, z_dir=l1 % 0)) as top_support:
        Circle(cross_member_od/2)
        Circle(cross_member_id/2,mode=Mode.SUBTRACT)
    sweep(path=side_support_frame)

    with BuildLine() as side_support_frame:
        p1 = front_rail_edge.position_at(front_rail_edge.length
                                         - side_support_offset - side_support_adjustment,
                                         position_mode=PositionMode.LENGTH)
        a2 = back_frame.line.edges().sort_by(Axis.Z)[0]
        p2 = a2.position_at(a2.length - side_support_offset - 0.5*M,position_mode=PositionMode.LENGTH)
        l1 = Line([p1,p2])
    with BuildSketch(Plane(origin=l1 @ 0, z_dir=l1 % 0)) as top_support:
        Circle(cross_member_od/2)
        Circle(cross_member_id/2,mode=Mode.SUBTRACT)
    sweep(path=side_support_frame)


    with BuildLine() as brace_frame:
        a1 = back_frame.line.edges().sort_by(Axis.Z)[0]
        p1 = a1.position_at(a1.length - brace_offset,position_mode=PositionMode.LENGTH)
        a2 = back_frame.line.edges().sort_by(Axis.Z)[-1]
        p2 = a2.position_at(brace_offset,position_mode=PositionMode.LENGTH)
        l1 = Line([p1,p2])
    with BuildSketch(Plane(origin=l1 @ 0, z_dir=l1 % 0)) as brace:
        Circle(cross_member_od/2)
        Circle(cross_member_id/2,mode=Mode.SUBTRACT)
    sweep(path=brace_frame)

    a1 = back_frame.line.edges().sort_by(Axis.Z)[-1]
    p1 = a1.position_at(brace_offset + 50,position_mode=PositionMode.LENGTH).add((0,tube_od/2,0))
    with Locations(p1):
        Padeye(rotation=(0,0,0))


    # NOTE: the generic mirror() op deepcopies the part, and in build123d 0.11.1
    # deepcopy corrupts this geometry's curve parameters ("Geom_TrimmedCurve::
    # parameters out of range"). Mirror via the method (no deepcopy) and add() it.
    add(arch2.part.mirror(Plane(origin=(width/2,0,0),z_dir=(1,0,0))))


    with BuildLine() as center_support_frame:
        p1 = frame.line.edges().sort_by(Axis.Z)[-1].position_at(1)
        p2 = back_frame.line.edges().sort_by(Axis.Z)[-1].position_at(1)
        l1 = Line([p1,p2])
    with BuildSketch(Plane(origin=l1 @ 0, z_dir=l1 % 0)) as center_support_sk:
        Circle(cross_member_od/2)
        Circle(cross_member_id/2,mode=Mode.SUBTRACT)
    sweep(path=center_support_frame)

# --- Crude sailboat stern context model ----------------------------------
# The arch's own feet define the boat's mounting surfaces: the front feet
# (flat plates at z=0) sit on a horizontal deck, while the back feet (tilted
# plates at y≈1.0 m, z=-drop) sit on the sloping transom/scoop.  Rather than
# guess, measure the back foot's contact plane from the geometry just built
# and make that plane the hull's aft scoop surface — the hull then always
# matches the arch, whatever the parameters.
if show_boat:
    # bottom (contact) face of the back foot placed at back_points[0]
    back_bottoms = [f for f in back_foot_af.faces()
                    if f.geom_type is GeomType.PLANE
                    and f.normal_at(f.center()).Z < -0.5]
    if not back_bottoms:
        raise RuntimeError("could not locate the back-foot bottom face "
                           "(is back_foot_angle too small?)")
    back_bottom = min(back_bottoms,
                      key=lambda f: (f.center() - back_points[0]).length)
    transom_plane = Plane(origin=back_bottom.center(),
                          z_dir=-back_bottom.normal_at(back_bottom.center()))
    tn = transom_plane.z_dir
    if abs(tn.Y) < 0.01:
        raise RuntimeError("back-foot plate is not tilted along the boat "
                           "axis; keep back_foot_angle > 0 to build the hull")
    # Y where the transom plane meets deck level z=0 (top edge of the scoop)
    transom_edge_y = transom_plane.origin.Y - (tn.Z / tn.Y) * (0 - transom_plane.origin.Z)
    y_cut = transom_edge_y - hull_len_aft

    print(f"Boat context: transom plane origin "
          f"({transom_plane.origin.X:.0f}, {transom_plane.origin.Y:.0f}, "
          f"{transom_plane.origin.Z:.0f}) mm, normal "
          f"({tn.X:.3f}, {tn.Y:.3f}, {tn.Z:.3f})")
    print(f"  deck/scoop crease at y = {transom_edge_y/1000:.3f} m (z = 0), "
          f"hull from y = {y_cut/1000:.3f} m to {hull_aft_end/1000:.3f} m")

    with BuildPart() as boat:
        with BuildSketch(Plane.XY):
            Polygon((boat_cx - deck_width_aft/2, hull_aft_end),
                    (boat_cx + deck_width_aft/2, hull_aft_end),
                    (boat_cx + deck_width_fwd/2, y_cut),
                    (boat_cx - deck_width_fwd/2, y_cut))
        extrude(amount=hull_bottom_z)
        # Carve off the wedge above the transom plane so the aft top of the
        # hull is exactly the (scoop) plane the back feet rest on.
        with Locations(transom_plane):
            Box(length=10*M, width=10*M, height=2*M,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT)
else:
    boat = None

# --- Viewer, export, screenshot ------------------------------------------
if "--no-viewer" in sys.argv:
    print("viewer skipped (--no-viewer)")
elif show_boat:
    try:
        show(arch2, boat, names=["arch", "boat"],
             colors=[(0.85, 0.85, 0.9), (0.10, 0.45, 0.72)],
             alphas=[1.0, 0.85])
    except Exception as exc:
        print(f"viewer unavailable ({exc}); continuing without it")
else:
    show(arch2)

export_stl(arch2.part,'arch.stl')

if "--no-viewer" not in sys.argv:
    try:
        save_screenshot('arch.png')
    except Exception as exc:
        print(f"screenshot unavailable ({exc})")

mass_kg = part_mass(arch2.part)
feet_kg = 2 * volume_mass(front_foot_volume) + 2 * volume_mass(back_foot_volume)
print(f"Estimated mass (316 stainless steel): {mass_kg:.1f} kg")
print(f"  feet (4 x ArchFoot): {feet_kg:.2f} kg")
print(f"  structure (everything else): {mass_kg - feet_kg:.1f} kg")
if show_boat:
    print(f"Boat context hull volume: {boat.part.volume/1e9:.1f} m^3")

# --- Foot-to-hull fit check ----------------------------------------------
foot_names = ["front (port)", "front (starboard)", "back (port)", "back (starboard)"]
foot_centres = [Vector(0, 0, 0), Vector(width, 0, 0),
                Vector(*back_points[0]),
                Vector(width - back_inset, back_points[0][1], back_points[0][2])]

if show_boat:
    def deck_width_at(y):
        """Hull planform width at a given y (trapezoid between the cuts)."""
        return deck_width_aft + (deck_width_fwd - deck_width_aft) * \
            (hull_aft_end - y) / (hull_aft_end - y_cut)

    def plate_rim_points(face, radius=40, count=8):
        """Points on the plate bottom face, `radius` mm out from its centre."""
        c = face.center()
        n = face.normal_at(c)
        u = Vector(1, 0, 0) if abs(n.X) < 0.9 else Vector(0, 1, 0)
        u = (u - u.dot(n) * n).normalized()
        v = n.cross(u).normalized()
        return [c + radius * (cos(2*pi*i/count) * u + sin(2*pi*i/count) * v)
                for i in range(count)]

    print("\nFoot-to-hull fit (mm; rim gap ≈ 0 means the plate lies on the hull):")
    ok = True
    for name, centre in zip(foot_names, foot_centres):
        cands = [f for f in arch2.part.faces()
                 if f.geom_type is GeomType.PLANE
                 and (f.center() - centre).length < 25]
        bottoms = [f for f in cands if f.normal_at(f.center()).Z < -0.5]
        if not bottoms:
            print(f"  {name}: NO bottom face found near "
                  f"({centre.X:.0f}, {centre.Y:.0f}, {centre.Z:.0f})")
            ok = False
            continue
        bf = min(bottoms, key=lambda f: (f.center() - centre).length)
        gap = max(boat.part.distance_to(p) for p in plate_rim_points(bf))
        margin = deck_width_at(centre.Y) / 2 - 50 - abs(centre.X - boat_cx)
        flag = "" if gap < 0.5 and margin > 10 else "  <-- check!"
        if flag:
            ok = False
        print(f"  {name}: rim gap {gap:.2f} mm, hull-edge margin "
              f"{margin:.0f} mm{flag}")
    print("  fit OK" if ok else "  !! foot/hull fit problems — adjust hull widths")

