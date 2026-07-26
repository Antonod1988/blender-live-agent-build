import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())
from mathutils import noise as mnoise

C_ROAD = get_coll("Road")
R = rng(5150)

X0, X1 = -52.0, 66.0
Y0, Y1 = -30.0, 30.0
NX, NY = 300, 152
HALF_ROAD = 2.45
RUT_Y = 1.02
BLEND = 5.0


def road_center(x):
    if x >= 0.0:
        return 3.6 * (1.0 - math.cos(x / 32.0))
    return -2.4 * (1.0 - math.cos(x / 28.0))


def road_bed(x):
    """Longitudinal profile of the carriageway: near level, gently undulating."""
    return -0.10 + 0.30 * math.sin((x + 14.0) / 40.0) - 0.30 * math.sin(14.0 / 40.0)


def field(x, y):
    h = mnoise.fractal(Vector((x * 0.013, y * 0.013, 0.0)), 0.5, 2.1, 4) * 0.62
    h += mnoise.fractal(Vector((x * 0.052 + 11.0, y * 0.052, 3.0)), 0.5, 2.0, 4) * 0.15
    h += mnoise.noise(Vector((x * 0.33, y * 0.33, 7.0))) * 0.035
    return h


def road_profile(x, y):
    d = abs(y - road_center(x))
    if d < HALF_ROAD:
        k = 1.0
    elif d < HALF_ROAD + BLEND:
        t = (d - HALF_ROAD) / BLEND
        k = 1.0 - (t * t * (3.0 - 2.0 * t))
    else:
        k = 0.0

    crown = 0.05 * math.cos(min(d / HALF_ROAD, 1.0) * math.pi * 0.5)
    surf = road_bed(x) + crown
    h = field(x, y) * (1.0 - k) + surf * k

    if HALF_ROAD - 0.2 < d < HALF_ROAD + 1.3:
        t = (d - (HALF_ROAD - 0.2)) / 1.5
        h += 0.17 * math.sin(t * math.pi) ** 2

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


for name in ("Ground", "Cobbles"):
    ob = bpy.data.objects.get(name)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)
for me in list(bpy.data.meshes):
    if me.users == 0:
        bpy.data.meshes.remove(me)

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
    if abs(poly.center.y - road_center(poly.center.x)) < HALF_ROAD + 0.3:
        poly.material_index = 1

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
    cen = Vector((x, y, z + rz * (1.0 - R.uniform(0.40, 0.80))))
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

# --- drop the wheels back onto the new surface ------------------------------
contacts = {}
for name, radius in (("Wheel.RearL", 0.780), ("Wheel.RearR", 0.780),
                     ("Wheel.FrontL", 0.520), ("Wheel.FrontR", 0.520)):
    ob = bpy.data.objects[name]
    x, y = ob.location.x, ob.location.y
    g = ground_h(x, y)
    ob.location.z = g + radius - 0.040
    contacts[name] = (round(x, 3), round(y, 3), round(g, 3))

bpy.app.driver_namespace["road"] = {
    "center": road_center, "h": ground_h, "bed": road_bed,
    "half": HALF_ROAD, "rut": RUT_Y, "bounds": (X0, X1, Y0, Y1),
}
zs = [c[2] for c in contacts.values()]
bpy.app.driver_namespace["chassis"] = {
    "z_mean": sum(zs) / 4.0,
    "pitch": (((contacts["Wheel.FrontL"][2] + contacts["Wheel.FrontR"][2]) / 2.0)
              - ((contacts["Wheel.RearL"][2] + contacts["Wheel.RearR"][2]) / 2.0)) / 2.60,
}
__result__ = {"contacts": contacts, "chassis": bpy.app.driver_namespace["chassis"],
              "cobbles": placed}
print(__result__)
