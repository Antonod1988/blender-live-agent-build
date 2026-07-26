import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())
from mathutils import noise as mnoise

C_DET = get_coll("Details", get_coll("Carriage"))
C_ENV = get_coll("Environment")
road = bpy.app.driver_namespace["road"]
ground_h, road_center = road["h"], road["center"]
R = rng(777)

# dashboard in coach colours instead of a black slab
assign(bpy.data.objects["Box.Dashboard"], bpy.data.materials["Lacquer.Burgundy"])

# luggage leather: knock the value down so it stops shouting
tan = bpy.data.materials["Leather.Tan"].node_tree.nodes["Principled BSDF"]
tan.inputs["Base Color"].default_value = (0.085, 0.046, 0.023, 1.0)
tan.inputs["Roughness"].default_value = 0.72
# foliage: deeper, less minty
fol = bpy.data.materials["Plant.Foliage"].node_tree.nodes["Principled BSDF"]
fol.inputs["Base Color"].default_value = (0.030, 0.052, 0.021, 1.0)
bark = bpy.data.materials["Plant.Bark"].node_tree.nodes["Principled BSDF"]
bark.inputs["Base Color"].default_value = (0.040, 0.031, 0.024, 1.0)

# ---------------------------------------------------------------- road dressing
# cart ruts leading up to the wheels: churned dirt clods
bm = new_bm()
for _ in range(320):
    x = R.uniform(-16.0, 12.0)
    side = 1.0 if R.random() < 0.5 else -1.0
    y = road_center(x) + side * (road["rut"] + R.gauss(0.0, 0.26))
    z = ground_h(x, y)
    s = R.uniform(0.035, 0.11)
    cen = Vector((x, y, z + s * 0.35))
    verts = sphere(bm, cen, 1.0, segments=6, rings=4,
                   scale=(s, s * R.uniform(0.7, 1.4), s * R.uniform(0.4, 0.7)))
    for v in verts:
        v.co += Vector((mnoise.noise(v.co * 12.0), mnoise.noise(v.co * 12.0 + Vector((3, 0, 0))),
                        mnoise.noise(v.co * 12.0 + Vector((0, 3, 0))))) * (s * 0.5)
clods = bm_obj(bm, "Road.Clods", C_ENV, smooth=True)
assign(clods, bpy.data.materials["Ground.Roadbed"])

# dry weeds along the verge for silhouette interest
bm = new_bm()
for _ in range(260):
    x = R.uniform(-22.0, 24.0)
    side = 1.0 if R.random() < 0.5 else -1.0
    y = road_center(x) + side * R.uniform(road["half"] + 0.15, road["half"] + 3.2)
    z = ground_h(x, y)
    h = R.uniform(0.35, 0.85)
    a = R.uniform(0, TAU)
    lean = Vector((math.cos(a), math.sin(a), 0.0)) * R.uniform(0.06, 0.24)
    stalk = [tuple(Vector((x, y, z)) + lean * (t * t) + Vector((0, 0, h * t)))
             for t in (0.0, 0.35, 0.7, 1.0)]
    sweep(bm, stalk, rect_profile(0.010, 0.010, corner=0.004),
          scale=lambda t: 1.0 - 0.6 * t)
    # seed head
    sphere(bm, stalk[-1], 1.0, segments=6, rings=4, scale=(0.018, 0.018, 0.055))
weeds = bm_obj(bm, "Env.Weeds", C_ENV, smooth=True)
assign(weeds, bpy.data.materials["Plant.Grass"])

__result__ = {"added": ["Road.Clods", "Env.Weeds"]}
print(__result__)
