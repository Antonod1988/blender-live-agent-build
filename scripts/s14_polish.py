import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())
from mathutils import noise as mnoise

C_ENV = get_coll("Environment")
road = bpy.app.driver_namespace["road"]
ground_h, road_center = road["h"], road["center"]
R = rng(9091)

# ---- emissive bits: stop them blowing out to white discs -------------------
fl = bpy.data.materials["Flame.Core"].node_tree.nodes["Principled BSDF"]
fl.inputs["Emission Strength"].default_value = 16.0
fl.inputs["Emission Color"].default_value = (1.0, 0.48, 0.14, 1.0)
cr = bpy.data.materials["Crystal.Arcane"].node_tree.nodes["Principled BSDF"]
cr.inputs["Emission Strength"].default_value = 4.0
for nm in ("L", "R"):
    ob = bpy.data.objects.get("Lantern.%s.Flame" % nm)
    if ob:
        ob.scale = (0.65, 0.65, 0.8)
    li = bpy.data.objects.get("LanternLight.%s" % nm)
    if li:
        li.data.energy = 38.0
gem = bpy.data.objects.get("Harness.PoleGem")
if gem:
    gem.scale = (0.8, 0.8, 0.8)
gl = bpy.data.objects.get("PoleGemLight")
if gl:
    gl.data.energy = 7.0

# ---- foreground planting: shorter weeds, cleared near the lens -------------
CAM = Vector((10.2, -7.2, 0.0))
for n in ("Env.Weeds",):
    ob = bpy.data.objects.get(n)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)

bm = new_bm()
kept = 0
for _ in range(420):
    x = R.uniform(-24.0, 26.0)
    side = 1.0 if R.random() < 0.5 else -1.0
    y = road_center(x) + side * R.uniform(road["half"] + 0.15, road["half"] + 3.6)
    if (Vector((x, y, 0.0)) - CAM).length < 6.0:
        continue
    z = ground_h(x, y)
    h = R.uniform(0.22, 0.52)
    a = R.uniform(0, TAU)
    lean = Vector((math.cos(a), math.sin(a), 0.0)) * R.uniform(0.05, 0.18)
    stalk = [tuple(Vector((x, y, z)) + lean * (t * t) + Vector((0, 0, h * t)))
             for t in (0.0, 0.35, 0.7, 1.0)]
    sweep(bm, stalk, rect_profile(0.008, 0.008, corner=0.003),
          scale=lambda t: 1.0 - 0.6 * t)
    sphere(bm, stalk[-1], 1.0, segments=6, rings=4, scale=(0.014, 0.014, 0.042))
    kept += 1
weeds = bm_obj(bm, "Env.Weeds", C_ENV, smooth=True)
assign(weeds, bpy.data.materials["Plant.Grass"])

# thin the grass that crowds the lens: shrink blades closest to the camera
grass = bpy.data.objects.get("Env.Grass")
removed = 0
if grass:
    me = grass.data
    doomed = set()
    for p in me.polygons:
        c = p.center
        if (Vector((c.x, c.y, 0.0)) - CAM).length < 4.2:
            doomed.add(p.index)
    if doomed:
        bm2 = new_bm()
        bm2.from_mesh(me)
        bm2.faces.ensure_lookup_table()
        faces = [f for f in bm2.faces if f.index in doomed]
        bmesh.ops.delete(bm2, geom=faces, context="FACES")
        bm2.to_mesh(me)
        bm2.free()
        me.update()
        removed = len(doomed)

__result__ = {"weeds": kept, "grass_faces_cleared": removed}
print(__result__)
