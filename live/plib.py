"""plib - small modelling helpers for the pirate ship build.

Injected into the live Blender session by agent.py and re-injected whenever
this file changes. Stage scripts use it as `plib.<fn>`; the bridge also
exposes `director` and `hud` as plain globals.
"""

import bpy
import math
import random
from mathutils import Vector, Matrix, Quaternion

TAU = math.pi * 2.0
rad = math.radians


def V(*a):
    return Vector(a[0]) if len(a) == 1 else Vector(a)


def lerp(a, b, t):
    return a + (b - a) * t


def _cr(p0, p1, p2, p3, t):
    return 0.5 * ((2 * p1) + (-p0 + p2) * t
                  + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)


def spline(pts, n):
    """Catmull-Rom resample of a control polygon; works on any tuple width."""
    m = len(pts)
    if m < 2:
        return [tuple(pts[0])] * (n + 1)
    ext = [pts[0]] + [tuple(p) for p in pts] + [pts[-1]]
    out = []
    for i in range(n + 1):
        t = (i / float(n)) * (m - 1)
        k = min(int(t), m - 2)
        f = t - k
        p0, p1, p2, p3 = ext[k], ext[k + 1], ext[k + 2], ext[k + 3]
        out.append(tuple(_cr(a, b, c, d, f) for a, b, c, d in zip(p0, p1, p2, p3)))
    return out


# --------------------------------------------------------------- collections
def col(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def link(obj, collection=None):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


# ------------------------------------------------------------------- staging
class stage:
    """Idempotent build step: re-running deletes what the last run created."""

    def __init__(self, name, collection=None):
        self.name = name
        self.collection = collection
        self.before = set()

    def __enter__(self):
        doomed = [o for o in bpy.data.objects if o.get("_stage") == self.name]
        for o in doomed:
            bpy.data.objects.remove(o, do_unlink=True)
        self.before = set(bpy.data.objects.keys())
        return self

    def __exit__(self, *exc):
        if exc[0] is not None:
            return False
        made = [o for o in bpy.data.objects if o.name not in self.before]
        root = bpy.data.objects.get("ShipRoot")
        for o in made:
            o["_stage"] = self.name
            if self.collection is not None:
                link(o, self.collection)
            # everything is authored in ship space; the hull is assembled clear
            # of the water and settles onto its lines at the launch
            if root is not None and o is not root and o.parent is None:
                o.parent = root
        self.made = made
        return False


def purge():
    for block in (bpy.data.meshes, bpy.data.curves):
        for d in list(block):
            if d.users == 0:
                block.remove(d)


# -------------------------------------------------------------- mesh factory
def mesh(name, verts, faces, edges=(), collection=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], list(edges), [tuple(f) for f in faces])
    me.validate(verbose=False)
    me.update()
    ob = bpy.data.objects.new(name, me)
    return link(ob, collection)


def box(name, size, loc=(0, 0, 0), rot=(0, 0, 0), collection=None):
    sx, sy, sz = (s * 0.5 for s in size)
    v = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
         (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
         (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = mesh(name, v, f, collection=collection)
    return place(ob, loc, rot)


def lathe(name, profile, seg=24, arc=TAU, cap=True, loc=(0, 0, 0), rot=(0, 0, 0),
          collection=None):
    """Revolve a (radius, z) profile around Z. profile is ordered bottom->top."""
    prof = [(float(r), float(z)) for r, z in profile]
    closed = abs(arc - TAU) < 1e-6
    rings = seg if closed else seg + 1
    verts, faces = [], []
    for i in range(rings):
        a = arc * (i / float(seg))
        ca, sa = math.cos(a), math.sin(a)
        for r, z in prof:
            verts.append((r * ca, r * sa, z))
    n = len(prof)
    for i in range(seg if closed else seg):
        j = (i + 1) % rings
        for k in range(n - 1):
            a0, a1 = i * n + k, i * n + k + 1
            b0, b1 = j * n + k, j * n + k + 1
            faces.append((a0, b0, b1, a1))
    if cap and closed:
        base = len(verts)
        verts.append((0, 0, prof[0][1]))
        verts.append((0, 0, prof[-1][1]))
        for i in range(seg):
            j = (i + 1) % rings
            if prof[0][0] > 1e-6:
                faces.append((i * n, base, j * n))
            if prof[-1][0] > 1e-6:
                faces.append((j * n + n - 1, base + 1, i * n + n - 1))
    ob = mesh(name, verts, faces, collection=collection)
    return place(ob, loc, rot)


def cyl(name, r, h, seg=16, loc=(0, 0, 0), rot=(0, 0, 0), cap=True, collection=None):
    return lathe(name, [(r, -h * 0.5), (r, h * 0.5)], seg=seg, cap=cap,
                 loc=loc, rot=rot, collection=collection)


def loft(name, sections, cap_start=True, cap_end=True, closed_ring=True,
         collection=None):
    """Bridge equally sized point rings into a surface."""
    n = len(sections[0])
    verts, faces = [], []
    for sec in sections:
        assert len(sec) == n, "sections must share a point count"
        verts.extend([tuple(p) for p in sec])
    for s in range(len(sections) - 1):
        a, b = s * n, (s + 1) * n
        last = n if closed_ring else n - 1
        for k in range(last):
            k2 = (k + 1) % n
            faces.append((a + k, b + k, b + k2, a + k2))
    if cap_start:
        faces.append(tuple(range(n - 1, -1, -1)))
    if cap_end:
        o = (len(sections) - 1) * n
        faces.append(tuple(range(o, o + n)))
    return mesh(name, verts, faces, collection=collection)


def sweep(name, path, w, h, up=(0, 0, 1), collection=None):
    """Sweep a rectangular section along a path. w/h may be callables of t."""
    pts = [Vector(p) for p in path]
    n = len(pts) - 1
    secs = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n)] - pts[max(i - 1, 0)])
        if t.length < 1e-9:
            t = Vector((1, 0, 0))
        t.normalize()
        side = t.cross(Vector(up))
        if side.length < 1e-6:
            side = Vector((0, 1, 0))
        side.normalize()
        upv = side.cross(t).normalized()
        f = i / float(n) if n else 0.0
        hw = 0.5 * (w(f) if callable(w) else w)
        hh = 0.5 * (h(f) if callable(h) else h)
        secs.append([p - side * hw - upv * hh, p + side * hw - upv * hh,
                     p + side * hw + upv * hh, p - side * hw + upv * hh])
    return loft(name, secs, closed_ring=True, collection=collection)


def tube(name, points, radius=0.02, res=3, caps=True, collection=None, smooth_curve=False):
    """A round tube through a polyline - ropes, spars, rails."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    sp = cu.splines.new('NURBS' if smooth_curve else 'POLY')
    sp.points.add(len(points) - 1)
    for i, p in enumerate(points):
        sp.points[i].co = (p[0], p[1], p[2], 1.0)
    if smooth_curve:
        sp.use_endpoint_u = True
        sp.order_u = min(4, len(points))
    cu.bevel_depth = radius
    cu.bevel_resolution = res
    cu.use_fill_caps = caps
    ob = bpy.data.objects.new(name, cu)
    return link(ob, collection)


def spar(name, path, r, seg=14, collection=None, caps=True):
    """A round, tapered spar along a path - masts, yards, booms.

    sweep() gives a rectangular section, which is right for a keel and quite
    wrong for a mast; every stick of rigging goes through here instead.
    """
    pts = [Vector(p) for p in path]
    n = len(pts) - 1
    secs = []
    for i, p in enumerate(pts):
        t = pts[min(i + 1, n)] - pts[max(i - 1, 0)]
        if t.length < 1e-9:
            t = Vector((0.0, 0.0, 1.0))
        t.normalize()
        ref = Vector((0.0, 0.0, 1.0)) if abs(t.z) < 0.9 else Vector((1.0, 0.0, 0.0))
        u = t.cross(ref).normalized()
        v = t.cross(u).normalized()
        f = i / float(n) if n else 0.0
        rr = r(f) if callable(r) else r
        secs.append([p + u * (rr * math.cos(a)) + v * (rr * math.sin(a))
                     for a in [TAU * k / seg for k in range(seg)]])
    ob = loft(name, secs, cap_start=caps, cap_end=caps, closed_ring=True,
              collection=collection)
    smooth(ob, 40.0)
    return ob


def tubes(name, polylines, radius=0.02, res=2, collection=None):
    """Many ropes in ONE curve object - rigging is hundreds of lines."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    for pts in polylines:
        if len(pts) < 2:
            continue
        sp = cu.splines.new('POLY')
        sp.points.add(len(pts) - 1)
        for i, p in enumerate(pts):
            sp.points[i].co = (p[0], p[1], p[2], 1.0)
    cu.bevel_depth = radius
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    ob = bpy.data.objects.new(name, cu)
    return link(ob, collection)


def catenary(a, b, sag=0.25, steps=12):
    """Points of a rope hanging between a and b."""
    a, b = Vector(a), Vector(b)
    out = []
    for i in range(steps + 1):
        t = i / float(steps)
        p = a.lerp(b, t)
        p.z -= sag * math.sin(math.pi * t)
        out.append(p)
    return out


# ----------------------------------------------------------------- transform
def place(obj, loc=None, rot=None, scale=None):
    if loc is not None:
        obj.location = loc
    if rot is not None:
        obj.rotation_euler = rot
    if scale is not None:
        obj.scale = scale if hasattr(scale, "__len__") else (scale, scale, scale)
    return obj


def dup(obj, name=None, loc=None, rot=None, scale=None, collection=None):
    ob = obj.copy()
    ob.data = obj.data.copy()
    if name:
        ob.name = name
    link(ob, collection or (obj.users_collection[0] if obj.users_collection else None))
    return place(ob, loc, rot, scale)


def instance(obj, name=None, loc=None, rot=None, scale=None, collection=None):
    """Share the mesh datablock - cheap for repeated parts (cannons, blocks)."""
    ob = bpy.data.objects.new(name or (obj.name + ".i"), obj.data)
    link(ob, collection or (obj.users_collection[0] if obj.users_collection else None))
    return place(ob, loc, rot, scale)


def join(objs, name=None):
    objs = [o for o in objs if o]
    if len(objs) < 2:
        return objs[0] if objs else None
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    out = bpy.context.view_layer.objects.active
    if name:
        out.name = name
    out.select_set(False)
    return out


def apply_mods(obj):
    bpy.context.view_layer.objects.active = obj
    for m in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except Exception:
            pass
    return obj


# ----------------------------------------------------------------- modifiers
def bevel(obj, width=0.01, segments=2, angle=40.0, clamp=True):
    m = obj.modifiers.new("bevel", 'BEVEL')
    m.width = width
    m.segments = segments
    m.limit_method = 'ANGLE'
    m.angle_limit = rad(angle)
    m.use_clamp_overlap = clamp
    m.harden_normals = False
    return obj


def subsurf(obj, levels=1, render=2, simple=False):
    m = obj.modifiers.new("subsurf", 'SUBSURF')
    m.levels = levels
    m.render_levels = render
    m.subdivision_type = 'SIMPLE' if simple else 'CATMULL_CLARK'
    return obj


def solidify(obj, thickness=0.02, offset=-1.0):
    m = obj.modifiers.new("solidify", 'SOLIDIFY')
    m.thickness = thickness
    m.offset = offset
    # even offset spikes wildly where faces meet at a near-zero angle, and a
    # lofted cap always has such a vertex; a plain offset never explodes
    m.use_even_offset = False
    return obj


def mirror(obj, axis=(False, True, False), obj_ref=None, bisect=False):
    m = obj.modifiers.new("mirror", 'MIRROR')
    m.use_axis = axis
    m.use_bisect_axis = (bisect, bisect, bisect) if bisect else (False, False, False)
    if obj_ref:
        m.mirror_object = obj_ref
    return obj


def array(obj, count, offset=(0, 0, 0), relative=False):
    m = obj.modifiers.new("array", 'ARRAY')
    m.count = count
    m.use_relative_offset = relative
    m.use_constant_offset = not relative
    if relative:
        m.relative_offset_displace = offset
    else:
        m.constant_offset_displace = offset
    return obj


def displace(obj, tex, strength=0.2, mid=0.5, coords='LOCAL'):
    m = obj.modifiers.new("displace", 'DISPLACE')
    m.texture = tex
    m.strength = strength
    m.mid_level = mid
    m.texture_coords = coords
    return obj


def smooth(obj, angle=32.0):
    for p in obj.data.polygons:
        p.use_smooth = True
    if angle is None:
        return obj
    try:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.shade_auto_smooth(angle=rad(angle))
        obj.select_set(False)
    except Exception:
        pass
    return obj


def noise_tex(name, scale=1.0, depth=2, kind='STUCCI'):
    t = bpy.data.textures.get(name)
    if t is None:
        t = bpy.data.textures.new(name, type=kind)
    t.noise_scale = scale
    if hasattr(t, "noise_depth"):
        t.noise_depth = depth
    return t


# ----------------------------------------------------------------- materials
def sock(node, key, out=False):
    """Resolve a socket by name, preferring the ENABLED one.

    Multi-type nodes (Mix, Map Range, Switch) carry one socket per data type,
    all sharing a name. Lookup by name returns the first - usually the float -
    and links into a disabled socket are silently dropped, which reads as
    'my node graph does nothing'.
    """
    coll = node.outputs if out else node.inputs
    if isinstance(key, int):
        return coll[key]
    for s in coll:
        if s.name == key and s.enabled:
            return s
    return coll[key]


def _set(node, key, val):
    try:
        sock(node, key).default_value = val
    except Exception:
        pass


def nodes(mat):
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    out = nt.nodes.get("Material Output")
    return nt, bsdf, out


def _n(nt, kind, loc=(0, 0), **kw):
    node = nt.nodes.new(kind)
    node.location = loc
    for k, v in kw.items():
        if "." in k:
            a, b = k.split(".")
            setattr(getattr(node, a), b, v)
        else:
            setattr(node, k, v)
    return node


def _l(nt, a, sa, b, sb):
    nt.links.new(sock(a, sa, out=True), sock(b, sb))


def pbr(name, color=(0.5, 0.5, 0.5, 1), rough=0.5, metal=0.0, **kw):
    """Fetch-or-create a plain principled material."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
    nt, bsdf, out = nodes(mat)
    if len(color) == 3:
        color = tuple(color) + (1.0,)
    _set(bsdf, "Base Color", color)
    _set(bsdf, "Roughness", rough)
    _set(bsdf, "Metallic", metal)
    for k, v in kw.items():
        _set(bsdf, k.replace("_", " ").title().replace("Ior", "IOR"), v)
    return mat


def assign(obj, mat, slot=None):
    if obj.data is None:
        return obj
    if slot is None:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    else:
        while len(obj.data.materials) <= slot:
            obj.data.materials.append(None)
        obj.data.materials[slot] = mat
    return obj


def assign_all(objs, mat):
    for o in objs:
        assign(o, mat)
    return objs


def face_mat(obj, mat, pred):
    """Add mat as a second slot and give it every face matching pred(center)."""
    idx = len(obj.data.materials)
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        if pred(p.center, p.normal):
            p.material_index = idx
    return obj
