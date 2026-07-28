"""Which guns touch which timbers, and where does every rigging line end?"""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

for win in bpy.context.window_manager.windows:
    for area in win.screen.areas:
        if area.type == 'VIEW_3D':
            with bpy.context.temp_override(window=win, area=area):
                if bpy.context.screen.is_animation_playing:
                    bpy.ops.screen.animation_cancel(restore_frame=False)
            break
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()


def tri(ob):
    ev = ob.evaluated_get(dg)
    try:
        me = ev.to_mesh()
    except Exception:
        return None
    if not me or not len(me.polygons):
        ev.to_mesh_clear()
        return None
    mw = ob.matrix_world
    vs = [mw @ v.co for v in me.vertices]
    ps = [list(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return BVHTree.FromPolygons(vs, ps)


guns, timbers = [], []
for ob in bpy.data.objects:
    if ob.type != 'MESH':
        continue
    if ob.name.startswith("Gun.") or ob.name.startswith("Cannon."):
        guns.append(ob)
    elif any(k in ob.name for k in ("Beam", "Deck.", "Bulwark", "Xtree",
                                    "Trestle", "Cross", "Break", "Waterway",
                                    "Channel", "Deadeye", "Rail", "Moulding",
                                    "Wale", "Plank", "Gun1", "Port", "Mast",
                                    "Ladder", "Hatch", "Capstan")):
        timbers.append(ob)

trees = {}
hits = []
for g in guns:
    tg = trees.setdefault(g.name, tri(g))
    if tg is None:
        continue
    for t in timbers:
        tt = trees.setdefault(t.name, tri(t))
        if tt is None:
            continue
        ov = tg.overlap(tt)
        if ov:
            hits.append((g.name, t.name, len(ov)))
hits.sort(key=lambda h: -h[2])

# every rigging polyline: where does each end sit, and on what?
ropes = []
for ob in bpy.data.objects:
    if ob.type != 'CURVE':
        continue
    if not ob.name.startswith(("Stays", "Shroud", "Lift", "Lanyard", "Chain")):
        continue
    mw = ob.matrix_world
    for si, sp in enumerate(ob.data.splines):
        pts = [mw @ Vector(p.co[:3]) for p in sp.points]
        if len(pts) < 2:
            continue
        ropes.append((ob.name, si,
                      [round(c, 1) for c in pts[0]],
                      [round(c, 1) for c in pts[-1]]))

__result__ = {"gun_timber_hits": hits[:16], "hit_count": len(hits),
              "rope_sample": ropes[:6], "rope_count": len(ropes)}
