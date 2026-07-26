import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())
from mathutils import noise as mnoise

C_ENV = get_coll("Environment")
road = bpy.app.driver_namespace["road"]
ground_h = road["h"]
R = rng(4242)

for n in ("Env.TreeTrunks", "Env.Foliage"):
    ob = bpy.data.objects.get(n)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)

M_BARK = bpy.data.materials["Plant.Bark"]
M_FOLI = bpy.data.materials["Plant.Foliage"]

# ---------------------------------------------------------------- distant trees
bm_t, bm_f = new_bm(), new_bm()
TREES = [
    (-28.0, 16.0, 1.15), (-41.0, -19.0, 1.30), (-19.0, 24.0, 0.95),
    (24.0, 21.0, 1.10), (36.0, -20.0, 1.00), (46.0, 15.0, 1.25),
    (-34.0, -28.0, 1.20), (12.0, 27.0, 0.90), (-8.0, 31.0, 1.05),
    (52.0, -26.0, 1.15), (30.0, 33.0, 1.30), (-48.0, 9.0, 1.10),
    (18.0, -24.0, 0.95), (-14.0, -26.0, 1.05),
]
for tx, ty, ts in TREES:
    tz = ground_h(tx, ty)
    lean = Vector((R.uniform(-0.09, 0.09), R.uniform(-0.09, 0.09), 0.0))
    H = 4.6 * ts
    trunk = []
    for i in range(9):
        t = i / 8.0
        trunk.append(tuple(Vector((tx, ty, tz - 0.2)) + lean * (t * t * H) + Vector((0, 0, H * t))))
    sweep(bm_t, trunk, rect_profile(0.34 * ts, 0.34 * ts, corner=0.15 * ts),
          scale=lambda t: 1.0 - 0.66 * t)
    tops = []
    for _b in range(R.randint(4, 6)):
        a = R.uniform(0, TAU)
        ln = R.uniform(1.1, 2.1) * ts
        start = Vector(trunk[R.randint(4, 6)])
        end = start + Vector((math.cos(a) * ln, math.sin(a) * ln, ln * R.uniform(0.6, 1.1)))
        sweep(bm_t, [tuple(start), tuple((start + end) * 0.5 + Vector((0, 0, 0.2))), tuple(end)],
              rect_profile(0.10 * ts, 0.10 * ts, corner=0.045 * ts),
              scale=lambda t: 1.0 - 0.6 * t)
        tops.append(end)
    tops.append(Vector(trunk[-1]))
    for base in tops:
        for _c in range(R.randint(3, 5)):
            cc = base + Vector((R.gauss(0, 0.55), R.gauss(0, 0.55), R.gauss(0.35, 0.30)))
            rad = R.uniform(0.55, 0.95) * ts
            verts = sphere(bm_f, tuple(cc), rad, segments=10, rings=6, scale=(1.0, 1.0, 0.8))
            for v in verts:
                v.co += Vector((mnoise.noise(v.co * 1.7),
                                mnoise.noise(v.co * 1.7 + Vector((5, 0, 0))),
                                mnoise.noise(v.co * 1.7 + Vector((0, 5, 0))))) * (rad * 0.42)
trunks = bm_obj(bm_t, "Env.TreeTrunks", C_ENV, smooth=True)
assign(trunks, M_BARK)
foli = bm_obj(bm_f, "Env.Foliage", C_ENV, smooth=True)
assign(foli, M_FOLI)

# ---------------------------------------------------------------- lighting
scn = bpy.context.scene
nt = scn.world.node_tree
sky = next(n for n in nt.nodes if n.type == "TEX_SKY")
bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
sky.sun_elevation = math.radians(7.5)
sky.sun_rotation = math.radians(135.0)
sky.sun_intensity = 0.45
sky.air_density = 1.05
sky.dust_density = 1.9
sky.ozone_density = 1.2
bg.inputs["Strength"].default_value = 0.52

sun = bpy.data.objects["SunKey"]
sun.rotation_euler = (math.radians(75.0), 0.0, math.radians(225.0))
sun.data.energy = 6.2
sun.data.color = (1.0, 0.735, 0.46)
sun.data.angle = math.radians(1.2)

fill = bpy.data.objects["SkyFill"]
fill.location = (9.0, -8.0, 5.0)
fill.rotation_euler = (math.radians(58.0), 0.0, math.radians(48.0))
fill.data.energy = 220.0
fill.data.size = 12.0
fill.data.color = (0.52, 0.66, 1.0)

scn.view_settings.view_transform = "AgX"
scn.view_settings.look = "AgX - Medium High Contrast"
scn.view_settings.exposure = 0.15

__result__ = {"trees": len(TREES), "sun_dir_note": "backlit from -X/+Y",
              "foliage_verts": len(foli.data.vertices)}
print(__result__)
