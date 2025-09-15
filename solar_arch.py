from math import cos, atan
from build123d import *
from ocp_vscode import *

width= 3.5 * M
back_width = 3.0 * M
back_inset = (width - back_width)/2
height = 2 * M
depth = 1 * M
drop = 0.2 * M
back_foot_angle = 40

front_offset = 0.5 * M
back_offset = 0.3 * M
tube_od = 40 * MM
wall_thickness = 3 * MM
tube_id = tube_od - wall_thickness * 2
bend_radius = 5 * tube_od
rise_rate = 0
top_support_offset = 0.25 * M
side_support_offset = 0.1 * M
brace_offset = 0.5 * M

side_support_adjustment = (back_inset/height) * 250

points = [(0,0,0),
          (back_inset,front_offset,height),
          (back_inset+bend_radius,front_offset+ front_offset/height* bend_radius*rise_rate,height+bend_radius*rise_rate)]
if rise_rate:
    point2 = (width - points[-1][0], points[-1][1], points[-1][2])
else:
    points[2] = (width/2, points[-1][1], points[-1][2])

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
    tf = af.faces().sort_by(Axis.Z)[-4]  
    split(bisect_by=tf)
    add(af)
    add(arch.part)
    


    p1 = frame.line.edges().sort_by(Axis.Z)[-1].position_at(top_support_offset,position_mode=PositionMode.LENGTH)
    p2 = back_frame.line.edges().sort_by(Axis.Z)[-1].position_at(top_support_offset,position_mode=PositionMode.LENGTH)
    l1 = Line([p1,p2])
    with BuildSketch(Plane(origin=l1 @ 0, z_dir=l1 % 0)) as top_support:
        Circle(tube_od/2)
        Circle(tube_id/2,mode=Mode.SUBTRACT)
    sweep(path=l1)


    with BuildLine() as side_support_frame:
        a1 = frame.line.edges().sort_by(Axis.Z)[0]
        p1 = a1.position_at(a1.length -side_support_offset - side_support_adjustment,position_mode=PositionMode.LENGTH)
        a2 = back_frame.line.edges().sort_by(Axis.Z)[0]
        p2 = a2.position_at(a2.length - side_support_offset,position_mode=PositionMode.LENGTH)
        l1 = Line([p1,p2])
    with BuildSketch(Plane(origin=l1 @ 0, z_dir=l1 % 0)) as top_support:
        Circle(tube_od/2)
        Circle(tube_id/2,mode=Mode.SUBTRACT)
    sweep(path=side_support_frame)

    with BuildLine() as side_support_frame:
        a1 = frame.line.edges().sort_by(Axis.Z)[0]
        p1 = a1.position_at(a1.length -side_support_offset - side_support_adjustment,position_mode=PositionMode.LENGTH)
        a2 = back_frame.line.edges().sort_by(Axis.Z)[0]
        p2 = a2.position_at(a2.length - side_support_offset - 0.5*M,position_mode=PositionMode.LENGTH)
        l1 = Line([p1,p2])
    with BuildSketch(Plane(origin=l1 @ 0, z_dir=l1 % 0)) as top_support:
        Circle(tube_od/2)
        Circle(tube_id/2,mode=Mode.SUBTRACT)
    sweep(path=side_support_frame)


    with BuildLine() as brace_frame:
        a1 = back_frame.line.edges().sort_by(Axis.Z)[0]
        p1 = a1.position_at(a1.length - brace_offset,position_mode=PositionMode.LENGTH)
        a2 = back_frame.line.edges().sort_by(Axis.Z)[-1]
        p2 = a2.position_at(brace_offset,position_mode=PositionMode.LENGTH)
        l1 = Line([p1,p2])
    with BuildSketch(Plane(origin=l1 @ 0, z_dir=l1 % 0)) as brace:
        Circle(tube_od/2)
        Circle(tube_id/2,mode=Mode.SUBTRACT)
    sweep(path=brace_frame)

    a1 = back_frame.line.edges().sort_by(Axis.Z)[-1]
    p1 = a1.position_at(brace_offset + 50,position_mode=PositionMode.LENGTH)
    print(p1)
    p1 = p1.add((0,tube_od/2,0))
    print(p1)
    with Locations(p1):
        add(Padeye(rotation=(0,0,0)))


    mirror(about=Plane(origin=(width/2,0,0),z_dir=(1,0,0)))


    with BuildLine() as center_support_frame:
        p1 = frame.line.edges().sort_by(Axis.Z)[-1].position_at(1)
        p2 = back_frame.line.edges().sort_by(Axis.Z)[-1].position_at(1)
        l1 = Line([p1,p2])
    with BuildSketch(Plane(origin=l1 @ 0, z_dir=l1 % 0)) as center_support_sk:
        Circle(tube_od/2)
        Circle(tube_id/2,mode=Mode.SUBTRACT)
    sweep(path=center_support_frame)

#eye = Padeye()

#show(eye)
show(arch2)
#export_stl(arch2.part,'arch.stl')

