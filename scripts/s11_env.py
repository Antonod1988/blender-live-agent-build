import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())
from mathutils import noise as mnoise

C_ENV = get_coll("Environment")
road = bpy.app.driver_namespace["road"]
ground_h, road_center, HALF = road["h"], road["center"], road["half"]
R = rng(88123)

M_GRASS = bpy.data.materials["Plant.Grass"]
M_BARK = bpy.data.materials["Plant.Bark"]
M_FOLI = bpy.data.materials["Plant.Foliage"]
M_STONE = bpy.data.materials["Stone.Boulder"]
M_WATER = bpy.data.materials["Water.Puddle"]
M_OAK = bpy.data.materials["Wood.Oak"]
M_IRON = bpy.data.materials["Iron.Black"]
M_COBBLE = bpy.data.materials["Stone.Cobble"]

# ---------------------------------------------------------------- grass
bm = new_bm()
tufts = 0
for _ in range(4200):
    x = R.uniform(-26.0, 30.0)
    d = R.uniform(HALF - 0.15, HALF + 9.0)
    side = 1.0 if R.random() < 0.5 else -1.0
    y = road_center(x) + side * d
    # thin out with distance from camera
    if abs(x) > 12.0 and R.random() > 0.35:
        continue
    dens = mnoise.noise(Vector((x * 0.30, y * 0.30, 3.0))) * 0.5 + 0.5
    if R.random() > 0.35 + 0.65 * dens:
        continue
    z = ground_h(x, y)
    n_blades = R.randint(4, 8)
    lean_a = R.uniform(0, TAU)
    for _b in range(n_blades):
        a = lean_a + R.uniform(-1.0, 1.0)
        bx = x + R.gauss(0.0, 0.045)
        by = y + R.gauss(0.0, 0.045)
        h = R.uniform(0.10, 0.34) * (1.0 + 0.4 * dens)
        bend = R.uniform(0.05, 0.20)
        w0 = R.uniform(0.008, 0.014)
        dirv = Vector((math.cos(a), math.sin(a), 0.0))
        prev = None
        for i in range(5):
            t = i / 4.0
            c = Vector((bx, by, z)) + dirv * (bend * t * t * 1.6) + Vector((0, 0, h * t))
            w = w0 * (1.0 - t) ** 0.8
            perp = Vector((-dirv.y, dirv.x, 0.0))
            v1 = bm.verts.new(tuple(c - perp * w))
            v2 = bm.verts.new(tuple(c + perp * w))
            if prev:
                try:
                    bm.faces.new((prev[0], prev[1], v2, v1))
                except ValueError:
                    pass
            prev = (v1, v2)
    tufts += 1
grass = bm_obj(bm, "Env.Grass", C_ENV, smooth=True)
assign(grass, M_GRASS)

# ---------------------------------------------------------------- boulders
bm = new_bm()
for _ in range(90):
    x = R.uniform(-34.0, 40.0)
    d = R.uniform(HALF + 0.6, 16.0)
    y = road_center(x) + (1 if R.random() < 0.5 else -1) * d
    z = ground_h(x, y)
    s = R.uniform(0.16, 0.62)
    cen = Vector((x, y, z + s * R.uniform(0.15, 0.45)))
    verts = sphere(bm, cen, 1.0, segments=10, rings=6,
                   scale=(s, s * R.uniform(0.7, 1.3), s * R.uniform(0.5, 0.85)))
    for v in verts:
        p = v.co
        p += Vector((mnoise.noise(p * 3.1), mnoise.noise(p * 3.1 + Vector((7, 0, 0))),
                     mnoise.noise(p * 3.1 + Vector((0, 7, 0))))) * (s * 0.28)
        v.co = p
rocks = bm_obj(bm, "Env.Boulders", C_ENV, smooth=True)
assign(rocks, M_STONE)

# ---------------------------------------------------------------- trees
bm_t, bm_f = new_bm(), new_bm()
TREES = [(-16.0, 11.0, 1.0), (-24.0, -13.5, 1.25), (13.0, 14.0, 1.1),
         (22.0, -12.0, 0.95), (31.0, 9.0, 1.3), (-32.0, 8.0, 1.15),
         (8.0, -15.0, 1.05), (-9.0, 17.0, 0.9), (38.0, -16.0, 1.2)]
for tx, ty, ts in TREES:
    tz = ground_h(tx, ty)
    lean = Vector((R.uniform(-0.10, 0.10), R.uniform(-0.10, 0.10), 0.0))
    trunk = []
    H = 3.4 * ts
    for i in range(9):
        t = i / 8.0
        trunk.append(tuple(Vector((tx, ty, tz - 0.15)) + lean * (t * t * H)
                           + Vector((0, 0, H * t))))
    sweep(bm_t, trunk, rect_profile(0.30 * ts, 0.30 * ts, corner=0.13 * ts),
          scale=lambda t: 1.0 - 0.62 * t)
    top = Vector(trunk[-1])
    for _b in range(R.randint(3, 5)):
        a = R.uniform(0, TAU)
        ln = R.uniform(0.9, 1.7) * ts
        start = Vector(trunk[R.randint(4, 6)])
        end = start + Vector((math.cos(a) * ln, math.sin(a) * ln, ln * R.uniform(0.5, 0.95)))
        sweep(bm_t, [tuple(start), tuple((start + end) * 0.5 + Vector((0, 0, 0.15))), tuple(end)],
              rect_profile(0.09 * ts, 0.09 * ts, corner=0.04 * ts),
              scale=lambda t: 1.0 - 0.55 * t)
        for _c in range(2):
            cc = end + Vector((R.gauss(0, 0.35), R.gauss(0, 0.35), R.gauss(0.25, 0.25)))
            sphere(bm_f, tuple(cc), R.uniform(0.75, 1.25) * ts, segments=12, rings=8,
                   scale=(1.0, 1.0, 0.78))
    for _c in range(5):
        cc = top + Vector((R.gauss(0, 0.55), R.gauss(0, 0.55), R.gauss(0.45, 0.35)))
        sphere(bm_f, tuple(cc), R.uniform(0.95, 1.55) * ts, segments=12, rings=8,
               scale=(1.0, 1.0, 0.75))
trunks = bm_obj(bm_t, "Env.TreeTrunks", C_ENV, smooth=True)
assign(trunks, M_BARK)
foli = bm_obj(bm_f, "Env.Foliage", C_ENV, smooth=True)
assign(foli, M_FOLI)

# ---------------------------------------------------------------- signpost
bm = new_bm()
SX, SY = 5.6, 3.35
SZ = ground_h(SX, SY)
post = [(SX, SY, SZ - 0.25), (SX + 0.03, SY, SZ + 1.30), (SX + 0.05, SY, SZ + 2.45)]
sweep(bm, post, rect_profile(0.135, 0.135, corner=0.035), scale=lambda t: 1.0 - 0.22 * t)
# two arrow boards
for i, (zz, ang, ln) in enumerate(((2.16, math.radians(-38), 0.92),
                                   (1.82, math.radians(150), 0.78))):
    d = Vector((math.cos(ang), math.sin(ang), 0.0))
    base = Vector((SX + 0.05, SY, SZ + zz))
    pts = [tuple(base + d * 0.06), tuple(base + d * ln)]
    rows = []
    for k, p in enumerate(pts):
        p = Vector(p)
        perp = Vector((-d.y, d.x, 0.0))
        w = 0.028
        hgt = 0.135 if k == 0 else 0.10
        rows.append([tuple(p - perp * w - Vector((0, 0, hgt))),
                     tuple(p + perp * w - Vector((0, 0, hgt))),
                     tuple(p + perp * w + Vector((0, 0, hgt))),
                     tuple(p - perp * w + Vector((0, 0, hgt)))])
    loft(bm, rows, close_loop=True, cap_ends=True)
sign = bm_obj(bm, "Env.Signpost", C_ENV, smooth=False)
assign(sign, M_OAK)
bevel_obj(sign, width=0.010, segments=2)

bm = new_bm()
for zz in (2.16, 1.82):
    cyl(bm, (SX + 0.05, SY, SZ + zz), 0.022, 0.30, axis="Y", segments=10)
cone(bm, (SX + 0.05, SY, SZ + 2.50), 0.10, 0.01, 0.16, segments=10)
signiron = bm_obj(bm, "Env.SignpostIron", C_ENV, smooth=True)
assign(signiron, M_IRON)

# ---------------------------------------------------------------- milestone
bm = new_bm()
MX, MY = -5.4, -3.15
MZ = ground_h(MX, MY)
rows = []
for i in range(9):
    t = i / 8.0
    w = 0.26 * (1.0 - 0.20 * t)
    z = MZ - 0.20 + 0.85 * t
    bulge = 1.0 - 0.55 * max(0.0, t - 0.80) / 0.20
    rows.append([(MX - w, MY - w * 0.7, z), (MX + w, MY - w * 0.7, z),
                 (MX + w * bulge, MY + w * 0.7, z), (MX - w * bulge, MY + w * 0.7, z)])
loft(bm, rows, close_loop=True, cap_ends=True)
for v in bm.verts:
    v.co += Vector((mnoise.noise(v.co * 4.0), mnoise.noise(v.co * 4.0 + Vector((3, 0, 0))),
                    mnoise.noise(v.co * 4.0 + Vector((0, 3, 0))))) * 0.022
mile = bm_obj(bm, "Env.Milestone", C_ENV, smooth=True)
assign(mile, M_COBBLE)
bevel_obj(mile, width=0.010, segments=2)

# ---------------------------------------------------------------- puddles
bm = new_bm()
for px, side in ((-6.4, 1), (-3.1, -1), (4.8, 1), (9.5, -1), (14.0, 1), (-11.0, -1)):
    py = road_center(px) + side * (road["rut"] + R.uniform(-0.12, 0.12))
    pz = ground_h(px, py) + 0.012
    rx, ry = R.uniform(0.35, 0.85), R.uniform(0.18, 0.34)
    ring = []
    N = 26
    for i in range(N):
        a = TAU * i / N
        wob = 1.0 + 0.20 * math.sin(a * 3.0 + px)
        ring.append(bm.verts.new((px + math.cos(a) * rx * wob,
                                  py + math.sin(a) * ry * wob, pz)))
    bm.faces.new(ring)
puddles = bm_obj(bm, "Env.Puddles", C_ENV, smooth=False)
assign(puddles, M_WATER)

__result__ = {"grass_tufts": tufts, "grass_tris": len(grass.data.polygons),
              "trees": len(TREES), "objects": [o.name for o in C_ENV.objects]}
print(__result__)
