# Shared procedural helpers for the fantasy-carriage build.
# Loaded by every stage with: exec(open(LIB).read(), globals())
import math
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

TAU = math.pi * 2.0


# ---------------------------------------------------------------- collections


def get_coll(name, parent=None):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    root = parent or bpy.context.scene.collection
    if coll.name not in root.children:
        try:
            root.children.link(coll)
        except RuntimeError:
            pass
    return coll


def link(obj, coll):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


# ---------------------------------------------------------------- mesh basics


def new_bm():
    return bmesh.new()


def bm_obj(bm, name, coll, smooth=False):
    me = bpy.data.meshes.new(name + "Mesh")
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    obj = bpy.data.objects.new(name, me)
    link(obj, coll)
    return obj


def bbox(bm, center, size, rot=None):
    """Add an axis-aligned (optionally rotated) box to a bmesh."""
    mat = Matrix.Translation(Vector(center))
    if rot:
        mat = mat @ Euler(rot).to_matrix().to_4x4()
    mat = mat @ Matrix.Diagonal(Vector((size[0], size[1], size[2], 1.0)))
    res = bmesh.ops.create_cube(bm, size=1.0, matrix=mat)
    return res["verts"]


def cyl(bm, center, radius, depth, axis="Z", segments=24, rot=None, cap=True):
    mat = Matrix.Translation(Vector(center))
    if axis == "X":
        mat = mat @ Matrix.Rotation(math.pi / 2, 4, "Y")
    elif axis == "Y":
        mat = mat @ Matrix.Rotation(math.pi / 2, 4, "X")
    if rot:
        mat = mat @ Euler(rot).to_matrix().to_4x4()
    res = bmesh.ops.create_cone(
        bm,
        cap_ends=cap,
        cap_tris=False,
        segments=segments,
        radius1=radius,
        radius2=radius,
        depth=depth,
        matrix=mat,
    )
    return res["verts"]


def cone(bm, center, r1, r2, depth, axis="Z", segments=20, rot=None):
    mat = Matrix.Translation(Vector(center))
    if axis == "X":
        mat = mat @ Matrix.Rotation(math.pi / 2, 4, "Y")
    elif axis == "Y":
        mat = mat @ Matrix.Rotation(math.pi / 2, 4, "X")
    if rot:
        mat = mat @ Euler(rot).to_matrix().to_4x4()
    res = bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=segments,
        radius1=r1,
        radius2=r2,
        depth=depth,
        matrix=mat,
    )
    return res["verts"]


def sphere(bm, center, radius, segments=20, rings=12, scale=(1, 1, 1)):
    mat = Matrix.Translation(Vector(center)) @ Matrix.Diagonal(
        Vector((scale[0], scale[1], scale[2], 1.0))
    )
    res = bmesh.ops.create_uvsphere(
        bm, u_segments=segments, v_segments=rings, radius=radius, matrix=mat
    )
    return res["verts"]


def revolve(bm, profile, segments=32, axis=(0, 0, 1), center=(0, 0, 0), angle=TAU):
    """Revolve a 2D profile [(r, z), ...] around an axis. Returns created geometry."""
    verts = [bm.verts.new((p[0], 0.0, p[1])) for p in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    geom = verts + edges
    bmesh.ops.spin(
        bm,
        geom=geom,
        cent=Vector(center),
        axis=Vector(axis),
        dvec=Vector((0, 0, 0)),
        angle=angle,
        steps=segments,
        use_merge=True,
    )
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    return geom


def loft(bm, sections, close_loop=True, cap_ends=True):
    """Bridge a list of equal-length vertex rings (each a list of (x,y,z))."""
    rings = []
    for sec in sections:
        rings.append([bm.verts.new(Vector(p)) for p in sec])
    faces = []
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        rng = range(n) if close_loop else range(n - 1)
        for i in rng:
            j = (i + 1) % n
            try:
                faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
            except ValueError:
                pass
    if cap_ends and close_loop:
        for ring, flip in ((rings[0], True), (rings[-1], False)):
            try:
                f = bm.faces.new(ring[::-1] if flip else ring)
                faces.append(f)
            except ValueError:
                pass
    return rings, faces


def bevel_obj(obj, width=0.006, segments=2, angle=math.radians(35)):
    m = obj.modifiers.new("Bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    m.angle_limit = angle
    m.harden_normals = False
    return m


def shade_smooth(obj, angle=math.radians(38)):
    for p in obj.data.polygons:
        p.use_smooth = True
    m = obj.modifiers.new("SmoothByAngle", "WEIGHTED_NORMAL") if False else None
    obj.data.use_auto_smooth = True if hasattr(obj.data, "use_auto_smooth") else False
    if hasattr(obj.data, "auto_smooth_angle"):
        obj.data.auto_smooth_angle = angle
    return obj


def solidify(obj, thickness=0.02, offset=-1.0):
    m = obj.modifiers.new("Solidify", "SOLIDIFY")
    m.thickness = thickness
    m.offset = offset
    return m


def mirror_y(obj):
    m = obj.modifiers.new("Mirror", "MIRROR")
    m.use_axis[0] = False
    m.use_axis[1] = True
    return m


def sweep(bm, path, profile, up=(0.0, 0.0, 1.0), caps=True, twist=None, scale=None):
    """Sweep a closed 2D profile [(u, v), ...] along a 3D path, frame by frame."""
    up = Vector(up)
    pts = [Vector(p) for p in path]
    rings = []
    for i, p in enumerate(pts):
        if i == 0:
            t = (pts[1] - pts[0])
        elif i == len(pts) - 1:
            t = (pts[-1] - pts[-2])
        else:
            t = (pts[i + 1] - pts[i - 1])
        t.normalize()
        n = up.cross(t)
        if n.length < 1e-6:
            n = Vector((1.0, 0.0, 0.0)).cross(t)
        n.normalize()
        b = t.cross(n)
        b.normalize()
        if twist is not None:
            a = twist(i / max(len(pts) - 1, 1))
            n2 = n * math.cos(a) + b * math.sin(a)
            b = -n * math.sin(a) + b * math.cos(a)
            n = n2
        s = scale(i / max(len(pts) - 1, 1)) if scale else 1.0
        rings.append([tuple(p + n * (u * s) + b * (v * s)) for u, v in profile])
    return loft(bm, rings, close_loop=True, cap_ends=caps)


def rect_profile(w, h, corner=0.0, steps=2):
    """Rounded rectangle profile centred on origin."""
    if corner <= 0.0:
        return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    c = min(corner, w / 2, h / 2)
    pts = []
    quads = [(w / 2 - c, h / 2 - c, 0.0), (-w / 2 + c, h / 2 - c, math.pi / 2),
             (-w / 2 + c, -h / 2 + c, math.pi), (w / 2 - c, -h / 2 + c, 1.5 * math.pi)]
    for cx, cy, a0 in quads:
        for s in range(steps + 1):
            a = a0 + (math.pi / 2) * s / steps
            pts.append((cx + math.cos(a) * c, cy + math.sin(a) * c))
    return pts


def arc_path(center, radius, a0, a1, steps, plane="XZ", squash=1.0, y=None):
    pts = []
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        c, s = math.cos(a) * radius, math.sin(a) * radius * squash
        if plane == "XZ":
            pts.append((center[0] + c, center[1] if y is None else y, center[2] + s))
        elif plane == "XY":
            pts.append((center[0] + c, center[1] + s, center[2]))
        else:
            pts.append((center[0], center[1] + c, center[2] + s))
    return pts


# ---------------------------------------------------------------- curves


def curve_from_points(name, points, coll, depth=0.02, resolution=6, cyclic=False,
                      spline="POLY", tilt=None, radii=None):
    cu = bpy.data.curves.new(name + "Curve", "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = 4
    cu.bevel_depth = depth
    cu.bevel_resolution = resolution
    cu.use_fill_caps = True
    sp = cu.splines.new(spline)
    sp.points.add(len(points) - 1) if spline == "POLY" else sp.bezier_points.add(len(points) - 1)
    if spline == "POLY":
        for i, p in enumerate(points):
            sp.points[i].co = (p[0], p[1], p[2], 1.0)
            if radii:
                sp.points[i].radius = radii[i]
    else:
        for i, p in enumerate(points):
            bp = sp.bezier_points[i]
            bp.co = Vector(p)
            bp.handle_left_type = bp.handle_right_type = "AUTO"
            if radii:
                bp.radius = radii[i]
    sp.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, cu)
    link(obj, coll)
    return obj


def arc_points(center, radius, a0, a1, steps, plane="XZ", squash=1.0):
    pts = []
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        c, s = math.cos(a) * radius, math.sin(a) * radius * squash
        if plane == "XZ":
            pts.append((center[0] + c, center[1], center[2] + s))
        elif plane == "XY":
            pts.append((center[0] + c, center[1] + s, center[2]))
        else:  # YZ
            pts.append((center[0], center[1] + c, center[2] + s))
    return pts


# ---------------------------------------------------------------- materials


def mat(name, base=(0.5, 0.5, 0.5), metallic=0.0, rough=0.5, spec=0.5,
        emission=None, emission_strength=0.0, alpha=1.0, ior=1.45,
        coat=0.0, sheen=0.0, transmission=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = nt.nodes.get("Material Output") or nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs[0], out.inputs[0])

    def setv(key, value):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = value

    rgba = tuple(base) + (1.0,) * (4 - len(base))
    setv("Base Color", rgba[:4])
    setv("Metallic", metallic)
    setv("Roughness", rough)
    setv("Specular IOR Level", spec)
    setv("IOR", ior)
    setv("Alpha", alpha)
    setv("Transmission Weight", transmission)
    setv("Coat Weight", coat)
    setv("Sheen Weight", sheen)
    if emission is not None:
        setv("Emission Color", tuple(emission) + (1.0,))
        setv("Emission Strength", emission_strength)
    if alpha < 1.0 or transmission > 0.0:
        m.blend_method = "BLEND" if hasattr(m, "blend_method") else m.blend_method
        try:
            m.use_backface_culling = False
        except AttributeError:
            pass
    return m


def add_noise_bump(material, scale=40.0, detail=8.0, strength=0.25, distortion=0.0):
    """Wire a Noise -> Bump chain into the Principled normal input."""
    nt = material.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf is None:
        return material
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Detail"].default_value = detail
    if "Distortion" in tex.inputs:
        tex.inputs["Distortion"].default_value = distortion
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    tex.location = (-700, -300)
    bump.location = (-400, -300)
    return material


def add_color_variation(material, color_a, color_b, scale=8.0, detail=6.0):
    """Blend two base colours through a noise mask for non-flat surfaces."""
    nt = material.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Detail"].default_value = detail
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = tuple(color_a) + (1.0,)
    ramp.color_ramp.elements[1].color = tuple(color_b) + (1.0,)
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[1].position = 0.65
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    tex.location = (-900, 300)
    ramp.location = (-600, 300)
    return material


def assign(obj, material):
    if obj.data is None:
        return obj
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)
    return obj


def assign_slots(obj, materials):
    obj.data.materials.clear()
    for m in materials:
        obj.data.materials.append(m)
    return obj


def set_face_material(obj, index, predicate):
    """Assign material slot `index` to faces satisfying predicate(face_center)."""
    me = obj.data
    for poly in me.polygons:
        c = poly.center
        if predicate(c):
            poly.material_index = index
    return obj


# ---------------------------------------------------------------- misc


def joint(objs, name, coll):
    """Join a list of mesh objects into one (data-level, no bpy.ops)."""
    bm = bmesh.new()
    for o in objs:
        me = o.to_mesh()
        tmp = bmesh.new()
        tmp.from_mesh(me)
        tmp.transform(o.matrix_world)
        tmp.to_mesh(me)
        bm.from_mesh(me)
        o.to_mesh_clear()
    out = bm_obj(bm, name, coll)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    return out


def parent_to(children, parent):
    for c in children:
        c.parent = parent
        c.matrix_parent_inverse = parent.matrix_world.inverted()
    return parent


def empty(name, location, coll, kind="PLAIN_AXES", size=0.3):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = kind
    e.empty_display_size = size
    e.location = location
    link(e, coll)
    return e


def rng(seed):
    r = random.Random(seed)
    return r
