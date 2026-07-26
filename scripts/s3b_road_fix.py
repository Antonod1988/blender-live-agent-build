import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())
from mathutils import noise as mnoise

scn = bpy.context.scene
C_ROAD = get_coll("Road")
R = rng(20260726)

# ---- sky: cleaner golden-hour gradient, no world volume ---------------------
nt = scn.world.node_tree
for l in list(nt.links):
    if l.to_socket.name == "Volume":
        nt.links.remove(l)
for n in list(nt.nodes):
    if n.type == "VOLUME_SCATTER":
        nt.nodes.remove(n)
sky = next(n for n in nt.nodes if n.type == "TEX_SKY")
sky.sun_elevation = math.radians(9.0)
sky.sun_rotation = math.radians(212.0)
sky.sun_intensity = 0.9
sky.altitude = 60.0
sky.air_density = 1.15
sky.dust_density = 1.35
sky.ozone_density = 1.1
next(n for n in nt.nodes if n.type == "BACKGROUND").inputs["Strength"].default_value = 1.15

sun = bpy.data.objects["SunKey"]
sun.data.energy = 3.4
sun.data.color = (1.0, 0.855, 0.66)
sun.rotation_euler = (math.radians(72.0), 0.0, math.radians(46.0))
fill = bpy.data.objects["SkyFill"]
fill.data.energy = 420.0
fill.data.color = (0.62, 0.74, 1.0)

# ---- rebuild the ground with a calmer landscape ----------------------------
for name in ("Ground", "Cobbles"):
    ob = bpy.data.objects.get(name)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)
for me in list(bpy.data.meshes):
    if me.users == 0:
        bpy.data.meshes.remove(me)

X0, X1 = -52.0, 66.0
Y0, Y1 = -30.0, 30.0
NX, NY = 330, 170
HALF_ROAD = 2.45
RUT_Y = 1.02


def road_center(x):
    if x >= 0.0:
        return 3.6 * (1.0 - math.cos(x / 32.0))
    return -2.4 * (1.0 - math.cos(x / 28.0))


def terrain_base(x, y):
    h = mnoise.fractal(Vector((x * 0.0125, y * 0.0125, 0.0)), 0.5, 2.1, 4) * 0.85
    h += mnoise.fractal(Vector((x * 0.055 + 11.0, y * 0.055, 3.0)), 0.5, 2.0, 4) * 0.16
    h += mnoise.noise(Vector((x * 0.35, y * 0.35, 7.0))) * 0.035
    return h


def road_profile(x, y):
    d = abs(y - road_center(x))
    base = terrain_base(x, y)
    if d < HALF_ROAD:
        k = 1.0
    elif d < HALF_ROAD + 1.8:
        t = (d - HALF_ROAD) / 1.8
        k = 1.0 - (t * t * (3.0 - 2.0 * t))
    else:
        k = 0.0

    bed = terrain_base(x, road_center(x)) - 0.13
    crown = 0.05 * math.cos(min(d / HALF_ROAD, 1.0) * math.pi * 0.5)
    surf = bed + crown
    h = base * (1.0 - k) + surf * k

    if HALF_ROAD - 0.2 < d < HALF_ROAD + 1.3:
        t = (d - (HALF_ROAD - 0.2)) / 1.5
        h += 0.19 * math.sin(t * math.pi) ** 2

    if k > 0.05:
        for side in (-1.0, 1.0):
            wob = 0.11 * math.sin(x * 0.29 + side * 1.7) + 0.05 * math.sin(x * 0.83)
            dy = y - (road_center(x) + side * RUT_Y + wob)
            depth = 0.085 * math.exp(-(dy / 0.28) ** 2)
            depth *= 0.78 + 0.22 * math.sin(x * 1.7 + side)
            h -= depth * k
        h += mnoise.fractal(Vector((x * 0.85, y * 0.85, 21.0)), 0.55, 2.0, 3) * 0.020 * k
    h += mnoise.fractal(Vector((x * 2.4, y * 2.4, 41.0)), 0.5, 2.0, 3) * 0.010
    return h, k


def ground_h(x, y):
    return road_profile(x, y)[0]


bm = new_bm()
grid = []
for i in range(NX + 1):
    x = X0 + (X1 - X0) * i / NX
    row = []
    for j in range(NY + 1):
        y = Y0 + (Y1 - Y0) * j / NY
        row.append(bm.verts.new((x, y, road_profile(x, y)[0])))
    grid.append(row)
for i in range(NX):
    gi, gn = grid[i], grid[i + 1]
    for j in range(NY):
        bm.faces.new((gi[j], gn[j], gn[j + 1], gi[j + 1]))

ground = bm_obj(bm, "Ground", C_ROAD, smooth=True)
assign_slots(ground, [bpy.data.materials["Ground.Dirt"],
                      bpy.data.materials["Ground.Roadbed"]])
for poly in ground.data.polygons:
    c = poly.center
    if abs(c.y - road_center(c.x)) < HALF_ROAD + 0.3:
        poly.material_index = 1

# ---- cobbles, denser near camera ------------------------------------------
bm = new_bm()
placed = 0
for _ in range(2600):
    x = R.uniform(X0 + 6, X1 - 6)
    off = R.gauss(0.0, 1.35)
    if abs(off) > HALF_ROAD - 0.15:
        continue
    y = road_center(x) + off
    rut_dist = min(abs(abs(off) - RUT_Y), 1.0)
    if R.random() > 0.22 + 0.78 * rut_dist:
        continue
    if abs(x) > 14.0 and R.random() > 0.30:
        continue
    z = ground_h(x, y)
    rx = R.uniform(0.07, 0.17)
    ry = rx * R.uniform(0.75, 1.3)
    rz = rx * R.uniform(0.40, 0.62)
    sink = R.uniform(0.40, 0.80)
    cen = Vector((x, y, z + rz * (1.0 - sink)))
    verts = sphere(bm, cen, 1.0, segments=8, rings=5, scale=(rx, ry, rz))
    rot = Matrix.Rotation(R.uniform(0, TAU), 4, "Z") @ Matrix.Rotation(R.uniform(-0.2, 0.2), 4, "X")
    for v in verts:
        p = cen + rot @ (v.co - cen)
        p.z += mnoise.noise(p * 9.0) * rz * 0.30
        p.x += mnoise.noise(p * 7.0 + Vector((5, 0, 0))) * rx * 0.22
        v.co = p
    placed += 1

cobbles = bm_obj(bm, "Cobbles", C_ROAD, smooth=True)
assign(cobbles, bpy.data.materials["Stone.Cobble"])

# store the ground function parameters for later stages
bpy.app.driver_namespace["road"] = {
    "center": road_center, "h": ground_h, "half": HALF_ROAD, "rut": RUT_Y,
    "bounds": (X0, X1, Y0, Y1),
}

__result__ = {"ground_verts": len(ground.data.vertices), "cobbles": placed,
              "z_at_origin": round(ground_h(0.0, 0.0), 3)}
print(__result__)
