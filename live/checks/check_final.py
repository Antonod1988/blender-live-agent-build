"""Three questions a screenshot cannot answer.

1. is the hull actually closed where the planking meets the transom?
2. is anything floating with nothing near it?
3. does every rope end land on something?

The ship rocks on drivers, so playback is stopped and every world matrix is
cached up front - otherwise the geometry is sampled at a dozen different
positions and every answer is nonsense.
"""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import ship

# --- freeze the sea state
for win in bpy.context.window_manager.windows:
    for area in win.screen.areas:
        if area.type == 'VIEW_3D':
            with bpy.context.temp_override(window=win, area=area):
                if bpy.context.screen.is_animation_playing:
                    bpy.ops.screen.animation_cancel(restore_frame=False)
            break
bpy.context.view_layer.update()

dg = bpy.context.evaluated_depsgraph_get()
report = {}
STRUCT = ("Hull", "Super", "Deck", "Rig", "Details", "Guns", "Sails")

root = bpy.data.objects["ShipRoot"]
SHIP = root.matrix_world.copy()

items = []                                   # (object, cached world matrix)
for cname in STRUCT:
    c = bpy.data.collections.get(cname)
    for ob in (c.all_objects if c else []):
        if ob.type in ('MESH', 'CURVE'):
            items.append((ob, ob.matrix_world.copy()))

geom = {}                                    # name -> (world verts, polys)
span = {}                                    # name -> (first tri, last tri)
verts, polys = [], []
for ob, mw in items:
    ev = ob.evaluated_get(dg)
    try:
        me = ev.to_mesh()
    except Exception:
        continue
    if me and len(me.polygons):
        vs = [mw @ v.co for v in me.vertices]
        ps = [list(p.vertices) for p in me.polygons]
        geom[ob.name] = (vs, ps)
        base = len(verts)
        start = len(polys)
        verts.extend(vs)
        polys.extend([[k + base for k in p] for p in ps])
        span[ob.name] = (start, len(polys))
    ev.to_mesh_clear()

tree = BVHTree.FromPolygons(verts, polys)
report["tris_in_tree"] = len(polys)

# ----------------------------------------- 1. is the stern actually closed?
gaps = []
if "Transom" in geom:
    vs, ps = geom["Transom"]
    tt = BVHTree.FromPolygons(vs, ps)
    for i in range(0, ship.STRAKES + 1, 2):
        # ship.point is in SHIP space; the mesh tree is in world space
        p = SHIP @ Vector(ship.point(ship.X_STERN, i / float(ship.STRAKES)))
        hit = tt.find_nearest(p, 3.0)
        gaps.append(round(99.0 if hit[0] is None else (hit[0] - p).length, 3))
report["stern_gap_m"] = {"max": max(gaps) if gaps else None,
                         "mean": round(sum(gaps) / len(gaps), 3) if gaps else None}

# ------------------------------------------------------------- 2. floaters
REACH = 1.1
floaters = []
for ob, mw in items:
    if ob.name not in geom:
        continue
    lo, hi = span[ob.name]
    vs, ps = geom[ob.name]
    # vertices alone are not enough: a spar built from two rings has all its
    # geometry at the ends, and the part it actually touches is the middle
    pts = list(vs)
    for f in ps:
        c = Vector((0.0, 0.0, 0.0))
        for k in f:
            c += vs[k]
        pts.append(c / len(f))
    step = max(1, len(pts) // 26)
    best = 99.0
    for p in pts[::step]:
        # every hit in reach, then drop the ones that are this object itself
        for loc, nor, idx, dist in tree.find_nearest_range(p, REACH):
            if lo <= idx < hi:
                continue
            best = min(best, (loc - p).length)
            if best < 0.05:
                break
        if best < 0.05:
            break
    if best > 0.30:
        floaters.append((ob.name, round(best, 2) if best < 99 else "adrift"))
floaters.sort(key=lambda t: (t[1] != "adrift", -(t[1] if t[1] != "adrift" else 0)))
report["floating"] = floaters[:16]
report["floating_count"] = len(floaters)

# ------------------------------------------------------------ 3. rope ends
loose = []
for ob, mw in items:
    if ob.type != 'CURVE':
        continue
    if not ob.name.startswith(("Stays", "Shroud", "Lift", "Bunt", "Sling",
                               "Anchor", "Gun.Breech", "Coil", "Top.")):
        continue
    for si, sp in enumerate(ob.data.splines):
        pts = [mw @ Vector(p.co[:3]) for p in sp.points]
        if len(pts) < 2:
            continue
        for tag, end in (("a", pts[0]), ("b", pts[-1])):
            hit = tree.find_nearest(end, 6.0)
            d = 99.0 if hit[0] is None else (hit[0] - end).length
            if d > 0.40:
                loose.append(("%s[%d].%s" % (ob.name, si, tag), round(d, 2)))
loose.sort(key=lambda t: -t[1])
report["loose_rope_ends"] = loose[:14]
report["loose_count"] = len(loose)

__result__ = report
