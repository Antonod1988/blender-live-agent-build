"""Orc-tech helpers: nothing is straight, nothing is measured, everything is bolted."""
import math
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector
from mathutils import noise as mnoise

TAU = math.pi * 2.0


def get_coll(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    root = parent or bpy.context.scene.collection
    if c.name not in root.children:
        try:
            root.children.link(c)
        except RuntimeError:
            pass
    return c


def new_bm():
    return bmesh.new()


def bm_obj(bm, name, coll, smooth=False, mat=None, bevel=None, split=None):
    me = bpy.data.meshes.new(name + "Mesh")
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    if mat is not None:
        ob.data.materials.append(bpy.data.materials[mat] if isinstance(mat, str) else mat)
    if bevel:
        m = ob.modifiers.new("Bevel", "BEVEL")
        m.width = bevel
        m.segments = 2
        m.limit_method = "ANGLE"
        m.angle_limit = math.radians(35)
    if split:
        ob.modifiers.new("EdgeSplit", "EDGE_SPLIT").split_angle = math.radians(split)
    return ob


def box(bm, center, size, rot=None):
    mat = Matrix.Translation(Vector(center))
    if rot:
        mat = mat @ Euler(rot).to_matrix().to_4x4()
    mat = mat @ Matrix.Diagonal(Vector((size[0], size[1], size[2], 1.0)))
    return bmesh.ops.create_cube(bm, size=1.0, matrix=mat)["verts"]


def cyl(bm, center, r, depth, axis="Z", seg=16, rot=None, cap=True):
    mat = Matrix.Translation(Vector(center))
    if axis == "X":
        mat = mat @ Matrix.Rotation(math.pi / 2, 4, "Y")
    elif axis == "Y":
        mat = mat @ Matrix.Rotation(math.pi / 2, 4, "X")
    if rot:
        mat = mat @ Euler(rot).to_matrix().to_4x4()
    return bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=seg,
                                 radius1=r, radius2=r, depth=depth, matrix=mat)["verts"]


def cone(bm, center, r1, r2, depth, axis="Z", seg=12, rot=None):
    mat = Matrix.Translation(Vector(center))
    if axis == "X":
        mat = mat @ Matrix.Rotation(math.pi / 2, 4, "Y")
    elif axis == "Y":
        mat = mat @ Matrix.Rotation(math.pi / 2, 4, "X")
    if rot:
        mat = mat @ Euler(rot).to_matrix().to_4x4()
    return bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                                 radius1=r1, radius2=r2, depth=depth, matrix=mat)["verts"]


def ball(bm, center, r, seg=12, rings=8, scale=(1, 1, 1)):
    mat = Matrix.Translation(Vector(center)) @ Matrix.Diagonal(
        Vector((scale[0], scale[1], scale[2], 1.0)))
    return bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings,
                                     radius=r, matrix=mat)["verts"]


def loft(bm, sections, closed=True, caps=True):
    rings = [[bm.verts.new(Vector(p)) for p in sec] for sec in sections]
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for i in (range(n) if closed else range(n - 1)):
            j = (i + 1) % n
            try:
                bm.faces.new((a[i], a[j], b[j], b[i]))
            except ValueError:
                pass
    if caps and closed:
        for ring, flip in ((rings[0], True), (rings[-1], False)):
            try:
                bm.faces.new(ring[::-1] if flip else ring)
            except ValueError:
                pass
    return rings


def sweep(bm, path, profile, up=(0, 0, 1), caps=True, scale=None):
    up = Vector(up)
    pts = [Vector(p) for p in path]
    rings = []
    for i, p in enumerate(pts):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == len(pts) - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        t.normalize()
        n = up.cross(t)
        if n.length < 1e-6:
            n = Vector((1, 0, 0)).cross(t)
        n.normalize()
        b = t.cross(n).normalized()
        s = scale(i / max(len(pts) - 1, 1)) if scale else 1.0
        rings.append([tuple(p + n * (u * s) + b * (v * s)) for u, v in profile])
    return loft(bm, rings, closed=True, caps=caps)


def rect(w, h, corner=0.0, steps=2):
    if corner <= 0:
        return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    c = min(corner, w / 2, h / 2)
    pts = []
    for cx, cy, a0 in ((w / 2 - c, h / 2 - c, 0.0), (-w / 2 + c, h / 2 - c, math.pi / 2),
                       (-w / 2 + c, -h / 2 + c, math.pi), (w / 2 - c, -h / 2 + c, 1.5 * math.pi)):
        for s in range(steps + 1):
            a = a0 + (math.pi / 2) * s / steps
            pts.append((cx + math.cos(a) * c, cy + math.sin(a) * c))
    return pts


# ------------------------------------------------------------------ orc-tech
def batter(verts, amount=0.02, freq=6.0, seed=0.0):
    """Hammer the geometry. Straight edges are for gits."""
    for v in verts:
        p = v.co
        d = Vector((mnoise.noise(p * freq + Vector((seed, 0, 0))),
                    mnoise.noise(p * freq + Vector((0, seed + 7, 0))),
                    mnoise.noise(p * freq + Vector((0, 0, seed + 13)))))
        v.co = p + d * amount


def plate(bm, outline_xz, y0, y1, dent=0.018, seed=0.0):
    """A cut steel plate: extrude an XZ outline between two Y planes, then batter it."""
    a = [(x, y0, z) for x, z in outline_xz]
    b = [(x, y1, z) for x, z in outline_xz]
    rings = loft(bm, [a, b], closed=True, caps=True)
    if dent:
        batter([v for r in rings for v in r], dent, 5.0, seed)
    return rings


def rivets(bm, points, r=0.028, h=0.022, axis="Y"):
    """Domed rivet heads. When in doubt, add more."""
    for p in points:
        cyl(bm, p, r, h, axis=axis, seg=8)
        off = {"X": (h * 0.5, 0, 0), "Y": (0, h * 0.5, 0), "Z": (0, 0, h * 0.5)}[axis]
        ball(bm, (p[0] + off[0], p[1] + off[1], p[2] + off[2]), r * 0.92, seg=8, rings=5,
             scale=(1, 1, 0.55) if axis == "Z" else
             ((0.55, 1, 1) if axis == "X" else (1, 0.55, 1)))


def rivet_line(a, b, n):
    a, b = Vector(a), Vector(b)
    return [tuple(a + (b - a) * (i / max(n - 1, 1))) for i in range(n)]


def spike(bm, base, direction, length, r=0.055, seg=7):
    d = Vector(direction).normalized()
    mid = Vector(base) + d * (length * 0.5)
    rot = d.to_track_quat("Z", "Y").to_euler()
    cone(bm, tuple(mid), r, 0.004, length, axis="Z", seg=seg, rot=tuple(rot))


def pipe(bm, pts, r, seg=10, taper=None):
    prof = [(math.cos(TAU * i / seg) * r, math.sin(TAU * i / seg) * r) for i in range(seg)]
    sweep(bm, pts, prof, scale=taper)


def chain(bm, a, b, links=9, r=0.035):
    a, b = Vector(a), Vector(b)
    span = b - a
    sag = span.length * 0.16
    for i in range(links):
        t = i / (links - 1.0)
        p = a + span * t - Vector((0, 0, 1)) * (math.sin(t * math.pi) * sag)
        rot = (0.0, math.pi / 2, 0.0) if i % 2 else (math.pi / 2, math.pi / 2, 0.0)
        bmesh.ops.create_cone(
            bm, cap_ends=False, segments=10, radius1=r, radius2=r, depth=r * 0.55,
            matrix=Matrix.Translation(p) @ Euler(rot).to_matrix().to_4x4())
        ring = bmesh.ops.create_circle(bm, cap_ends=False, segments=10, radius=r,
                                       matrix=Matrix.Translation(p) @
                                       Euler(rot).to_matrix().to_4x4())
        del ring


def rng(seed):
    return random.Random(seed)
