LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())
from mathutils import noise as mnoise

C_ROAD = get_coll("Road")
R = rng(20260726)

X0, X1 = -46.0, 62.0
Y0, Y1 = -26.0, 26.0
NX, NY = 300, 150
HALF_ROAD = 2.35        # carriageway half-width
RUT_Y = 0.98            # rut offset from the road centre
WHEEL_R_REAR = 0.78     # used later; ground is authored around it


def road_center(x):
    """Lateral centreline of the road: dead straight under the carriage, curving away."""
    if x >= 0.0:
        return 3.2 * (1.0 - math.cos(x / 30.0))
    return -2.2 * (1.0 - math.cos(x / 26.0))


def terrain_base(x, y):
    """Rolling ground before the road is cut into it."""
    h = mnoise.fractal(Vector((x * 0.021, y * 0.021, 0.0)), 0.55, 2.1, 5) * 2.6
    h += mnoise.fractal(Vector((x * 0.085 + 11.0, y * 0.085, 3.0)), 0.5, 2.0, 4) * 0.42
    h += mnoise.noise(Vector((x * 0.42, y * 0.42, 7.0))) * 0.055
    return h


def road_profile(x, y):
    """Returns (height, corridor_factor) for the finished road surface."""
    d = abs(y - road_center(x))
    base = terrain_base(x, y)

    # corridor mask: 1 on the carriageway, 0 out in the field
    if d < HALF_ROAD:
        k = 1.0
    elif d < HALF_ROAD + 1.5:
        t = (d - HALF_ROAD) / 1.5
        k = 1.0 - (t * t * (3.0 - 2.0 * t))
    else:
        k = 0.0

    # flatten the corridor towards a gently crowned road bed
    bed = terrain_base(x, road_center(x)) - 0.10
    crown = 0.055 * math.cos(min(d / HALF_ROAD, 1.0) * math.pi * 0.5)
    surf = bed + crown
    h = base * (1.0 - k) + surf * k

    # verge berm just outside the carriageway
    if HALF_ROAD - 0.15 < d < HALF_ROAD + 1.1:
        t = (d - (HALF_ROAD - 0.15)) / 1.25
        h += 0.16 * math.sin(t * math.pi) ** 2

    # twin wheel ruts, wandering slightly along the road
    if k > 0.05:
        for side in (-1.0, 1.0):
            wob = 0.10 * math.sin(x * 0.31 + side * 1.7) + 0.05 * math.sin(x * 0.87)
            dy = y - (road_center(x) + side * RUT_Y + wob)
            depth = 0.075 * math.exp(-(dy / 0.26) ** 2)
            depth *= 0.75 + 0.25 * math.sin(x * 1.9 + side)
            h -= depth * k
        # churned surface between and around the ruts
        h += mnoise.fractal(Vector((x * 0.9, y * 0.9, 21.0)), 0.55, 2.0, 4) * 0.022 * k

    # fine breakup everywhere
    h += mnoise.fractal(Vector((x * 2.6, y * 2.6, 41.0)), 0.5, 2.0, 3) * 0.012
    return h, k


def ground_h(x, y):
    return road_profile(x, y)[0]


# ---------------------------------------------------------------- ground mesh
bm = new_bm()
grid = []
for i in range(NX + 1):
    x = X0 + (X1 - X0) * i / NX
    row = []
    for j in range(NY + 1):
        y = Y0 + (Y1 - Y0) * j / NY
        h, _ = road_profile(x, y)
        row.append(bm.verts.new((x, y, h)))
    grid.append(row)
bm.verts.ensure_lookup_table()

for i in range(NX):
    for j in range(NY):
        bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))

ground = bm_obj(bm, "Ground", C_ROAD, smooth=True)
assign_slots(ground, [
    bpy.data.materials["Ground.Dirt"],
    bpy.data.materials["Ground.Roadbed"],
])
for poly in ground.data.polygons:
    c = poly.center
    if abs(c.y - road_center(c.x)) < HALF_ROAD + 0.25:
        poly.material_index = 1

# ---------------------------------------------------------------- cobblestones
bm = new_bm()
placed = 0
for _ in range(1500):
    x = R.uniform(X0 + 4, X1 - 4)
    off = R.gauss(0.0, 1.25)
    if abs(off) > HALF_ROAD - 0.12:
        continue
    y = road_center(x) + off
    # thin the stones out where the ruts have worn them away
    rut_dist = min(abs(abs(off) - RUT_Y), 1.0)
    if R.random() > 0.25 + 0.75 * rut_dist:
        continue
    # keep density high near the camera, sparse far away
    if abs(x) > 16.0 and R.random() > 0.45:
        continue
    z = ground_h(x, y)
    rx = R.uniform(0.075, 0.185)
    ry = rx * R.uniform(0.75, 1.25)
    rz = rx * R.uniform(0.45, 0.7)
    sink = R.uniform(0.35, 0.75)
    verts = sphere(bm, (x, y, z + rz * (1.0 - sink)), 1.0, segments=8, rings=5,
                   scale=(rx, ry, rz))
    ang = R.uniform(0, TAU)
    tilt = R.uniform(-0.25, 0.25)
    cen = Vector((x, y, z + rz * (1.0 - sink)))
    rot = (Matrix.Rotation(ang, 4, "Z") @ Matrix.Rotation(tilt, 4, "X"))
    for v in verts:
        v.co = cen + rot @ (v.co - cen)
        # rough the silhouette so stones do not read as eggs
        v.co.z += mnoise.noise(v.co * 9.0) * rz * 0.28
        v.co.x += mnoise.noise(v.co * 7.0 + Vector((5, 0, 0))) * rx * 0.20
    placed += 1

cobbles = bm_obj(bm, "Cobbles", C_ROAD, smooth=True)
assign(cobbles, bpy.data.materials["Stone.Cobble"])
bevel_obj(cobbles, width=0.004, segments=1)

__result__ = {
    "ground_verts": len(ground.data.vertices),
    "cobbles": placed,
    "cobble_tris": len(cobbles.data.polygons),
}
print(__result__)
