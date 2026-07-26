import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())

C_DET = get_coll("Details", get_coll("Carriage"))
C_INT = get_coll("Interior", get_coll("Carriage"))
GEO = bpy.app.driver_namespace["geo"]
B = bpy.app.driver_namespace["body"]
surf, normal_at, v_to_t = B["surf"], B["normal"], B["v_to_t"]
floor_z, roof_z, half_w = B["floor_z"], B["roof_z"], B["half_w"]
WINDOWS, X0, X1 = B["windows"], B["x0"], B["x1"]

M_GLASS = bpy.data.materials["Glass.Window"]
M_GLASSL = bpy.data.materials["Glass.Lantern"]
M_GOLD = bpy.data.materials["Gold.Ornament"]
M_GOLDD = bpy.data.materials["Gold.Dark"]
M_BRASS = bpy.data.materials["Brass.Fittings"]
M_IRON = bpy.data.materials["Iron.Black"]
M_VELVET = bpy.data.materials["Velvet.Crimson"]
M_LEATHER = bpy.data.materials["Leather.Black"]
M_EBONY = bpy.data.materials["Wood.Ebony"]
M_FLAME = bpy.data.materials["Flame.Core"]
M_SILVER = bpy.data.materials["Silver.Trim"]
M_CRYSTAL = bpy.data.materials["Crystal.Arcane"]
M_PANEL = bpy.data.materials["Panel.Inlay"]

# ---------------------------------------------------------------- glazing
bm = new_bm()
NG = 10
for _, xa, xb, va, vb in WINDOWS:
    for side in (1, -1):
        rows = []
        for i in range(NG + 1):
            x = xa + (xb - xa) * i / NG
            row = []
            for j in range(NG + 1):
                v = va + (vb - va) * j / NG
                t = v_to_t(v)
                p, n = surf(x, t), normal_at(x, t)
                if side < 0:
                    p, n = Vector((p.x, -p.y, p.z)), Vector((n.x, -n.y, n.z))
                row.append(tuple(p - n * 0.022))
            rows.append(row)
        for i in range(NG):
            for j in range(NG):
                bm.faces.new([bm.verts.new(rows[i][j]), bm.verts.new(rows[i + 1][j]),
                              bm.verts.new(rows[i + 1][j + 1]), bm.verts.new(rows[i][j + 1])])
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
glass = bm_obj(bm, "Body.Glazing", C_DET, smooth=True)
assign(glass, M_GLASS)
solidify(glass, thickness=0.006, offset=0.0)

# ---------------------------------------------------------------- interior
bm = new_bm()
bbox(bm, (0.0, 0.0, floor_z(0.0) + 0.035), (2.30, 1.20, 0.06))
ifloor = bm_obj(bm, "Int.Floor", C_INT, smooth=False)
assign(ifloor, M_EBONY)

bm = new_bm()
for sx, xseat in ((1, -0.72), (-1, 0.72)):
    # squab
    bbox(bm, (xseat, 0.0, 1.40), (0.52, 1.28, 0.16))
    # back rest leaning against the end wall
    rows = []
    for i in range(9):
        t = i / 8.0
        z = 1.48 + 0.52 * t
        x = xseat + sx * (0.22 + 0.10 * t)
        rows.append([(x - 0.06, -0.62, z), (x + 0.06, -0.62, z),
                     (x + 0.06, 0.62, z), (x - 0.06, 0.62, z)])
    loft(bm, rows, close_loop=True, cap_ends=True)
seats = bm_obj(bm, "Int.Seats", C_INT, smooth=True)
assign(seats, M_VELVET)
bevel_obj(seats, width=0.012, segments=2)

bm = new_bm()
for sx, xseat in ((1, -0.72), (-1, 0.72)):
    for i in range(3):
        for j in range(5):
            t = (i + 0.5) / 3.0
            z = 1.56 + i * 0.16
            y = -0.48 + j * 0.24
            bx = xseat + sx * (0.22 + 0.10 * t) + sx * -0.065
            sphere(bm, (bx, y, z), 0.014, segments=8, rings=5)
tuft = bm_obj(bm, "Int.Buttons", C_INT, smooth=True)
assign(tuft, M_GOLDD)

# headlining
bm = new_bm()
bbox(bm, (0.0, 0.0, roof_z(0.0) - 0.075), (2.34, 1.22, 0.05))
lining = bm_obj(bm, "Int.Headlining", C_INT, smooth=False)
assign(lining, M_PANEL)

# curtains gathered at the door window edges
bm = new_bm()
for _, xa, xb, va, vb in WINDOWS[:1]:
    for side in (1, -1):
        for edge in (xa + 0.05, xb - 0.05):
            rows = []
            for i in range(11):
                t = i / 10.0
                v = vb - (vb - va) * t
                tt = v_to_t(v)
                p, n = surf(edge, tt), normal_at(edge, tt)
                if side < 0:
                    p, n = Vector((p.x, -p.y, p.z)), Vector((n.x, -n.y, n.z))
                p = p - n * 0.055
                wob = 0.028 * math.sin(t * 5.0)
                ring = []
                for j in range(10):
                    a = TAU * j / 10
                    ring.append((p.x + math.cos(a) * (0.045 + wob),
                                 p.y - n.y * 0.0 + math.sin(a) * 0.02 * (1 if side > 0 else 1),
                                 p.z + math.sin(a) * 0.0 + 0.0))
                # build the fold ring in the plane of the window
                ring = []
                tangent = Vector((1.0, 0.0, 0.0))
                bnorm = n.cross(tangent).normalized()
                for j in range(10):
                    a = TAU * j / 10
                    off = tangent * (math.cos(a) * (0.05 + wob)) + n * (math.sin(a) * 0.028)
                    ring.append(tuple(p + off))
                rows.append(ring)
            loft(bm, rows, close_loop=True, cap_ends=True)
curtains = bm_obj(bm, "Int.Curtains", C_INT, smooth=True)
assign(curtains, M_VELVET)

# ---------------------------------------------------------------- door furniture
DOOR_X, DOOR_V = -0.18, -0.06
bm = new_bm()
for side in (1, -1):
    t = v_to_t(DOOR_V)
    p, n = surf(DOOR_X, t), normal_at(DOOR_X, t)
    if side < 0:
        p, n = Vector((p.x, -p.y, p.z)), Vector((n.x, -n.y, n.z))
    base = p + n * 0.012
    # back plate
    for r, d in ((0.052, 0.014), (0.030, 0.030)):
        cyl(bm, tuple(base + n * d * 0.5), r, d, segments=18,
            rot=(0.0, math.pi / 2, math.atan2(n.y, n.x)))
    # lever handle sweeping down
    handle = [tuple(base + n * 0.045),
              tuple(base + n * 0.075 + Vector((0.02, 0.0, -0.03))),
              tuple(base + n * 0.070 + Vector((0.05, 0.0, -0.085))),
              tuple(base + n * 0.052 + Vector((0.06, 0.0, -0.125)))]
    sweep(bm, handle, rect_profile(0.024, 0.020, corner=0.008))
    sphere(bm, handle[-1], 0.024, segments=12, rings=8)
    # hinges
    for vz in (0.42, -0.34):
        tt = v_to_t(vz)
        hp, hn = surf(-0.68, tt), normal_at(-0.68, tt)
        if side < 0:
            hp, hn = Vector((hp.x, -hp.y, hp.z)), Vector((hn.x, -hn.y, hn.z))
        cyl(bm, tuple(hp + hn * 0.018), 0.020, 0.115, segments=12,
            rot=(math.radians(90), 0, 0))
        bbox(bm, tuple(hp + hn * 0.010), (0.075, 0.030, 0.055))
handles = bm_obj(bm, "Door.Furniture", C_DET, smooth=True)
assign(handles, M_BRASS)

# ---------------------------------------------------------------- armorial crest
bm = new_bm()
for side in (1, -1):
    t = v_to_t(-0.30)
    p, n = surf(-0.19, t), normal_at(-0.19, t)
    if side < 0:
        p, n = Vector((p.x, -p.y, p.z)), Vector((n.x, -n.y, n.z))
    tangent = Vector((1.0, 0.0, 0.0))
    updir = n.cross(tangent).normalized()
    if updir.z < 0:
        updir = -updir
    # shield outline
    shield = []
    NS = 26
    for i in range(NS):
        a = TAU * i / NS
        u = math.cos(a) * 0.115
        w = math.sin(a)
        vv = (0.135 * w) if w > 0 else (0.175 * w * (1.0 - 0.55 * abs(math.cos(a)) ** 2))
        shield.append((u, vv))
    rows = []
    for k, off in ((0, 0.004), (1, 0.028)):
        scale_ = 1.0 if k == 0 else 0.94
        rows.append([tuple(p + n * off + tangent * (u * scale_) + updir * (vv * scale_))
                     for u, vv in shield])
    loft(bm, rows, close_loop=True, cap_ends=True)
    # crown of three points above the shield
    for dx in (-0.062, 0.0, 0.062):
        tip = p + n * 0.020 + tangent * dx + updir * 0.185
        cone(bm, tuple(tip), 0.020, 0.002, 0.055, axis="Z", segments=8)
        sphere(bm, tuple(tip + updir * 0.038), 0.016, segments=10, rings=6)
crest = bm_obj(bm, "Door.Crest", C_DET, smooth=True)
assign(crest, M_GOLD)
bevel_obj(crest, width=0.004, segments=2)

# a small arcane sigil set into each shield
bm = new_bm()
for side in (1, -1):
    t = v_to_t(-0.30)
    p, n = surf(-0.19, t), normal_at(-0.19, t)
    if side < 0:
        p, n = Vector((p.x, -p.y, p.z)), Vector((n.x, -n.y, n.z))
    sphere(bm, tuple(p + n * 0.036), 0.042, segments=14, rings=8, scale=(1, 1, 1))
sigil = bm_obj(bm, "Door.Sigil", C_DET, smooth=True)
assign(sigil, M_CRYSTAL)

# ---------------------------------------------------------------- folding step
bm = new_bm()
for side in (1, -1):
    y = side * (half_w(-0.18) * 0.86)
    for i, (dx, dz, w) in enumerate(((0.0, 0.86, 0.30), (0.10, 0.60, 0.34))):
        bbox(bm, (-0.18 + dx, y + side * 0.09, dz), (w, 0.20, 0.022))
    sweep(bm, [(-0.34, y + side * 0.02, 1.02), (-0.30, y + side * 0.10, 0.86),
               (-0.22, y + side * 0.12, 0.60)], rect_profile(0.030, 0.024, corner=0.006))
    sweep(bm, [(0.02, y + side * 0.02, 1.02), (0.02, y + side * 0.10, 0.86),
               (-0.02, y + side * 0.12, 0.60)], rect_profile(0.030, 0.024, corner=0.006))
step = bm_obj(bm, "Door.Step", C_DET, smooth=True)
assign(step, M_IRON)
bevel_obj(step, width=0.004, segments=2)

# ---------------------------------------------------------------- lanterns
def lantern(bm_frame, bm_glass, bm_flame, pos):
    px, py, pz = pos
    # bracket arm off the body
    # hexagonal cage
    for i in range(6):
        a = TAU * i / 6 + math.radians(30)
        cyl(bm_frame, (px + math.cos(a) * 0.095, py + math.sin(a) * 0.095, pz),
            0.010, 0.26, segments=6)
    for zz in (pz - 0.13, pz + 0.13):
        revolve(bm_frame, [(0.085, zz - 0.016), (0.112, zz - 0.016), (0.112, zz + 0.016),
                           (0.085, zz + 0.016), (0.085, zz - 0.016)], segments=24,
                center=(0, 0, 0))
    # the revolve above is centred at origin; move it into place afterwards
    # domed top with a chimney and finial
    revolve(bm_frame, [(0.0, pz + 0.30), (0.045, pz + 0.295), (0.085, pz + 0.245),
                       (0.115, pz + 0.175), (0.118, pz + 0.146)], segments=24)
    cyl(bm_frame, (0.0, 0.0, pz + 0.33), 0.028, 0.075, segments=12)
    sphere(bm_frame, (0.0, 0.0, pz + 0.385), 0.030, segments=12, rings=8)
    # base
    revolve(bm_frame, [(0.0, pz - 0.20), (0.075, pz - 0.20), (0.115, pz - 0.165),
                       (0.118, pz - 0.146)], segments=24)
    # glass drum
    revolve(bm_glass, [(0.100, pz - 0.128), (0.100, pz + 0.128)], segments=24)
    # candle and flame
    cyl(bm_flame, (0.0, 0.0, pz - 0.055), 0.022, 0.13, segments=10)
    sphere(bm_flame, (0.0, 0.0, pz + 0.045), 1.0, segments=10, rings=8,
           scale=(0.016, 0.016, 0.036))


for side in (1, -1):
    LP = (1.235, side * 0.735, 2.02)
    bmf, bmg, bmfl = new_bm(), new_bm(), new_bm()
    lantern(bmf, bmg, bmfl, (0.0, 0.0, 0.0))
    for bmx in (bmf, bmg, bmfl):
        bmesh.ops.translate(bmx, verts=bmx.verts[:], vec=Vector(LP))
    nm = "L" if side > 0 else "R"
    o1 = bm_obj(bmf, "Lantern.%s.Frame" % nm, C_DET, smooth=True)
    assign(o1, M_BRASS)
    o2 = bm_obj(bmg, "Lantern.%s.Glass" % nm, C_DET, smooth=True)
    assign(o2, M_GLASSL)
    o3 = bm_obj(bmfl, "Lantern.%s.Flame" % nm, C_DET, smooth=True)
    assign(o3, M_FLAME)

    # bracket
    bmb = new_bm()
    sweep(bmb, [(1.10, side * 0.62, 1.92), (1.18, side * 0.70, 1.98),
                (1.235, side * 0.735, 2.02)], rect_profile(0.032, 0.026, corner=0.008))
    sweep(bmb, [(1.14, side * 0.60, 2.20), (1.20, side * 0.70, 2.18),
                (1.235, side * 0.735, 2.19)], rect_profile(0.022, 0.018, corner=0.006))
    cyl(bmb, (1.235, side * 0.735, 2.20), 0.014, 0.10, segments=8)
    ob = bm_obj(bmb, "Lantern.%s.Bracket" % nm, C_DET, smooth=True)
    assign(ob, M_GOLD)

    # actual light source inside the lantern
    ld = bpy.data.lights.new("LanternLight.%s" % nm, "POINT")
    ld.energy = 55.0
    ld.color = (1.0, 0.66, 0.32)
    ld.shadow_soft_size = 0.06
    lo = bpy.data.objects.new("LanternLight.%s" % nm, ld)
    lo.location = (1.235, side * 0.735, 2.03)
    link(lo, C_DET)

__result__ = {"details": [o.name for o in C_DET.objects][:24],
              "interior": [o.name for o in C_INT.objects]}
print(__result__)
