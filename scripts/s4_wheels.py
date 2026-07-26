import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())
from mathutils import noise as mnoise

scn = bpy.context.scene
scn.view_settings.look = "AgX - Base Contrast"
C_WHEELS = get_coll("Wheels", get_coll("Carriage"))
road = bpy.app.driver_namespace["road"]
ground_h = road["h"]
road_center = road["center"]

M_TYRE = bpy.data.materials["Iron.Tyre"]
M_IRON = bpy.data.materials["Iron.Black"]
M_OAK = bpy.data.materials["Wood.Oak"]
M_GOLD = bpy.data.materials["Gold.Ornament"]
M_BRASS = bpy.data.materials["Brass.Fittings"]


def make_wheel(name, R, width, n_spokes, seed):
    """A built-up wheel: iron tyre, wooden felloes, dished spokes, banded hub.

    Built with its axle along local Z, then rotated so the axle runs along Y.
    """
    rr = rng(seed)
    parts = []

    felloe_out = R - 0.052
    felloe_in = R - 0.052 - (0.135 if R > 0.65 else 0.105)
    hub_r = 0.105 if R > 0.65 else 0.092

    # --- iron tyre --------------------------------------------------------
    bm = new_bm()
    prof = [(R - 0.050, -width * 0.46), (R + 0.004, -width * 0.50),
            (R + 0.004, width * 0.50), (R - 0.050, width * 0.46),
            (R - 0.050, -width * 0.46)]
    revolve(bm, prof, segments=72)
    tyre = bm_obj(bm, name + ".Tyre", C_WHEELS, smooth=True)
    assign(tyre, M_TYRE)
    parts.append(tyre)

    # --- wooden felloes (segmented rim) -----------------------------------
    bm = new_bm()
    n_fell = n_spokes // 2
    for i in range(n_fell):
        a0 = TAU * i / n_fell + 0.012
        a1 = TAU * (i + 1) / n_fell - 0.012
        steps = 7
        outer, inner = [], []
        for s in range(steps + 1):
            a = a0 + (a1 - a0) * s / steps
            outer.append((math.cos(a) * felloe_out, math.sin(a) * felloe_out))
            inner.append((math.cos(a) * felloe_in, math.sin(a) * felloe_in))
        ring = [(x, y, -width * 0.44) for x, y in outer] + \
               [(x, y, -width * 0.44) for x, y in reversed(inner)]
        top = [(x, y, width * 0.44) for x, y in outer] + \
              [(x, y, width * 0.44) for x, y in reversed(inner)]
        loft(bm, [ring, top], close_loop=True, cap_ends=True)
    felloe = bm_obj(bm, name + ".Felloe", C_WHEELS)
    assign(felloe, M_OAK)
    bevel_obj(felloe, width=0.008, segments=2)
    parts.append(felloe)

    # --- spokes: dished, tapered, octagonal -------------------------------
    bm = new_bm()
    for i in range(n_spokes):
        a = TAU * i / n_spokes + 0.04
        dish = (0.030 if i % 2 == 0 else -0.030) * (1.0 if R > 0.65 else 0.8)
        r0, r1 = hub_r - 0.012, felloe_in + 0.020
        rmid = (r0 + r1) * 0.5
        length = r1 - r0
        cen = (math.cos(a) * rmid, math.sin(a) * rmid, dish * 0.5)
        verts = cone(bm, cen, 0.036 if R > 0.65 else 0.030, 0.024, length,
                     axis="Z", segments=8, rot=(0.0, math.pi / 2, a))
        # tilt each spoke toward the hub dish plane
        for v in verts:
            t = (Vector((v.co.x, v.co.y, 0.0)).length - r0) / max(length, 1e-4)
            v.co.z += dish * (0.5 - t) * 0.9
    spokes = bm_obj(bm, name + ".Spokes", C_WHEELS, smooth=True)
    assign(spokes, M_OAK)
    parts.append(spokes)

    # --- hub: barrel body + iron bands + cap -----------------------------
    bm = new_bm()
    hp = [
        (0.0, -0.135), (0.052, -0.135), (0.062, -0.118),
        (hub_r * 0.86, -0.085), (hub_r, -0.030), (hub_r, 0.045),
        (hub_r * 0.90, 0.095), (0.070, 0.130), (0.048, 0.150), (0.0, 0.150),
    ]
    revolve(bm, hp, segments=40)
    hub = bm_obj(bm, name + ".Hub", C_WHEELS, smooth=True)
    assign(hub, M_OAK)
    parts.append(hub)

    bm = new_bm()
    for z, r in ((-0.100, hub_r * 0.93), (0.075, hub_r * 0.97)):
        band = [(r, z - 0.020), (r + 0.013, z - 0.022), (r + 0.013, z + 0.022),
                (r, z + 0.020), (r, z - 0.020)]
        revolve(bm, band, segments=40)
    # axle nut / hub cap
    cap = [(0.0, 0.150), (0.040, 0.150), (0.052, 0.170), (0.044, 0.196),
           (0.022, 0.208), (0.0, 0.210)]
    revolve(bm, cap, segments=24)
    bands = bm_obj(bm, name + ".HubBands", C_WHEELS, smooth=True)
    assign(bands, M_IRON)
    parts.append(bands)

    # --- gilded hub star + tyre nails ------------------------------------
    bm = new_bm()
    for i in range(8):
        a = TAU * i / 8
        cen = (math.cos(a) * 0.062, math.sin(a) * 0.062, 0.146)
        bbox(bm, cen, (0.052, 0.013, 0.011), rot=(0.0, 0.0, a))
    cyl(bm, (0.0, 0.0, 0.152), 0.028, 0.020, segments=16)
    star = bm_obj(bm, name + ".HubStar", C_WHEELS, smooth=False)
    assign(star, M_GOLD)
    bevel_obj(star, width=0.003, segments=2)
    parts.append(star)

    bm = new_bm()
    for i in range(n_fell):
        a = TAU * (i + 0.5) / n_fell
        for zz in (-width * 0.26, width * 0.26):
            cen = (math.cos(a) * (R - 0.030), math.sin(a) * (R - 0.030), zz)
            cyl(bm, cen, 0.014, 0.030, axis="Z", segments=8,
                rot=(0.0, math.pi / 2, a))
    nails = bm_obj(bm, name + ".Nails", C_WHEELS, smooth=True)
    assign(nails, M_IRON)
    parts.append(nails)

    # --- assemble: parent to an empty and lay the axle along Y ------------
    root = empty(name, (0, 0, 0), C_WHEELS, kind="CIRCLE", size=R)
    for p in parts:
        p.parent = root
    root.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    return root


WHEELS = []
spec = [
    ("Wheel.RearL", 0.780, 0.115, 14, -1.14, 0.98, 7301),
    ("Wheel.RearR", 0.780, 0.115, 14, -1.14, -0.98, 7302),
    ("Wheel.FrontL", 0.520, 0.100, 12, 1.46, 0.92, 7303),
    ("Wheel.FrontR", 0.520, 0.100, 12, 1.46, -0.92, 7304),
]
for name, R, w, ns, x, y, seed in spec:
    wh = make_wheel(name, R, w, ns, seed)
    z = ground_h(x, y) + R - 0.045          # sunk slightly into the rut
    wh.location = (x, y, z)
    wh.rotation_euler = (math.radians(90.0), math.radians(rng(seed).uniform(0, 360)), 0.0)
    WHEELS.append((name, round(x, 2), round(y, 2), round(z, 3)))

bpy.app.driver_namespace["wheels"] = {n: (x, y, z) for n, x, y, z in WHEELS}

__result__ = {"wheels": WHEELS,
              "objects": len([o for o in bpy.data.objects if o.name.startswith("Wheel")])}
print(__result__)
