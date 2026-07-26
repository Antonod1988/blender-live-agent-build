import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())

C_BODY = get_coll("Body", get_coll("Carriage"))
C_DET = get_coll("Details", get_coll("Carriage"))
GEO = bpy.app.driver_namespace["geo"]
B = bpy.app.driver_namespace["body"]
surf, v_to_t, roof_z, floor_z = B["surf"], B["v_to_t"], B["roof_z"], B["floor_z"]
X0, X1, HW = B["x0"], B["x1"], GEO["body_hw"]
XC, XH = (X0 + X1) * 0.5, (X1 - X0) * 0.5

M_BLACK = bpy.data.materials["Lacquer.Black"]
M_LACQ = bpy.data.materials["Lacquer.Burgundy"]
M_GOLD = bpy.data.materials["Gold.Ornament"]
M_IRON = bpy.data.materials["Iron.Black"]
M_LEATHER = bpy.data.materials["Leather.Black"]
M_TAN = bpy.data.materials["Leather.Tan"]
M_OAK = bpy.data.materials["Wood.Oak"]
M_EBONY = bpy.data.materials["Wood.Ebony"]
M_CANVAS = bpy.data.materials["Cloth.Canvas"]
M_BRASS = bpy.data.materials["Brass.Fittings"]

# deepen the lacquer so it reads burgundy, not salmon
bs = bpy.data.materials["Lacquer.Burgundy"].node_tree.nodes["Principled BSDF"]
bs.inputs["Base Color"].default_value = (0.072, 0.0075, 0.017, 1.0)

for n in ("Body.Roof",):
    ob = bpy.data.objects.get(n)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)

# ---------------------------------------------------------------- crowned roof
RX0, RX1 = X0 - 0.045, X1 + 0.045
NRX, NRT = 48, 44
rings = []
for i in range(NRX + 1):
    x = RX0 + (RX1 - RX0) * i / NRX
    xr = max(-1.0, min(1.0, (x - XC) / (XH + 0.045)))
    taper = 1.0 - 0.20 * max(0.0, abs(xr) - 0.80) / 0.20
    w = (HW * 1.045) * (1.0 - 0.05 * abs(xr) ** 3.0) * taper
    zb = roof_z(min(max(x, X0), X1))
    crown = 0.115 * (1.0 - 0.25 * xr * xr)
    ring = []
    for j in range(NRT):
        a = TAU * j / NRT
        cu, su = math.cos(a), math.sin(a)
        u = math.copysign(abs(cu) ** (2.0 / 4.5), cu)
        v = math.copysign(abs(su) ** (2.0 / 4.5), su)
        y = w * u * (1.0 - 0.12 * max(v, 0.0) ** 1.6)
        z = zb + 0.02 + 0.075 * v + crown * max(v, 0.0) * (1.0 - 0.55 * u * u)
        ring.append((x, y, z))
    rings.append(ring)
bm = new_bm()
loft(bm, rings, close_loop=True, cap_ends=True)
roof = bm_obj(bm, "Body.Roof", C_BODY, smooth=True)
assign(roof, M_BLACK)
roof.modifiers.new("EdgeSplit", "EDGE_SPLIT").split_angle = math.radians(34.0)
bevel_obj(roof, width=0.008, segments=2, angle=math.radians(26))


def roof_top(x):
    xr = max(-1.0, min(1.0, (x - XC) / (XH + 0.045)))
    return roof_z(min(max(x, X0), X1)) + 0.095 + 0.115 * (1.0 - 0.25 * xr * xr)


def roof_hw(x):
    xr = max(-1.0, min(1.0, (x - XC) / (XH + 0.045)))
    taper = 1.0 - 0.20 * max(0.0, abs(xr) - 0.80) / 0.20
    return (HW * 1.045) * (1.0 - 0.05 * abs(xr) ** 3.0) * taper


# ---------------------------------------------------------------- roof rail
bm = new_bm()
rail_pts = []
NR = 60
for i in range(NR):
    a = TAU * i / NR
    # rounded rectangle in plan, offset inside the roof edge
    cu, su = math.cos(a), math.sin(a)
    u = math.copysign(abs(cu) ** (2.0 / 5.0), cu)
    v = math.copysign(abs(su) ** (2.0 / 5.0), su)
    x = XC + (XH - 0.02) * u
    y = (roof_hw(x) - 0.055) * v
    rail_pts.append((x, y, roof_top(x) + 0.075))
rail_pts.append(rail_pts[0])
sweep(bm, rail_pts, rect_profile(0.020, 0.020, corner=0.006), caps=False)
# balusters
for i in range(0, NR, 3):
    x, y, z = rail_pts[i]
    cyl(bm, (x, y, z - 0.045), 0.010, 0.09, segments=8)
# corner finials
for sx in (-1, 1):
    for sy in (-1, 1):
        x = XC + sx * (XH - 0.10)
        y = sy * (roof_hw(x) - 0.075)
        z = roof_top(x)
        cyl(bm, (x, y, z + 0.045), 0.026, 0.09, segments=12)
        sphere(bm, (x, y, z + 0.118), 0.036, segments=14, rings=8)
        cone(bm, (x, y, z + 0.168), 0.020, 0.002, 0.07, segments=12)
rail = bm_obj(bm, "Roof.Rail", C_DET, smooth=True)
assign(rail, M_GOLD)

# ---------------------------------------------------------------- roof luggage
bm = new_bm()
bbox(bm, (-0.62, 0.0, roof_top(-0.62) + 0.20), (0.72, 0.86, 0.34))
trunk = bm_obj(bm, "Roof.Trunk", C_DET, smooth=False)
assign(trunk, M_TAN)
bevel_obj(trunk, width=0.020, segments=3)

bm = new_bm()
for dy in (-0.30, 0.30):
    sweep(bm, [(-0.62 + dy * 0.0, dy, roof_top(-0.62) + 0.375),
               (-0.98, dy, roof_top(-0.98) + 0.34),
               (-0.99, dy, roof_top(-0.99) + 0.03)],
          rect_profile(0.012, 0.075, corner=0.004))
    sweep(bm, [(-0.62 + dy * 0.0, dy, roof_top(-0.62) + 0.375),
               (-0.26, dy, roof_top(-0.26) + 0.34),
               (-0.25, dy, roof_top(-0.25) + 0.03)],
          rect_profile(0.012, 0.075, corner=0.004))
straps = bm_obj(bm, "Roof.TrunkStraps", C_DET, smooth=True)
assign(straps, M_LEATHER)

bm = new_bm()
for dy in (-0.30, 0.30):
    bbox(bm, (-0.62, dy, roof_top(-0.62) + 0.378), (0.10, 0.085, 0.020))
buckles = bm_obj(bm, "Roof.TrunkBuckles", C_DET, smooth=False)
assign(buckles, M_BRASS)
bevel_obj(buckles, width=0.003, segments=2)

# canvas-wrapped bundle beside the trunk
bm = new_bm()
sphere(bm, (0.35, 0.0, roof_top(0.35) + 0.16), 1.0, segments=18, rings=10,
       scale=(0.34, 0.40, 0.16))
bundle = bm_obj(bm, "Roof.Bundle", C_DET, smooth=True)
assign(bundle, M_CANVAS)

# ---------------------------------------------------------------- driver's box
BX0, BX1 = X1 - 0.02, 2.14
SEAT_Z = 1.86
bm = new_bm()
# floor of the box
bbox(bm, ((BX0 + BX1) * 0.5, 0.0, 1.505), (BX1 - BX0, 1.34, 0.075))
# side cheeks, curving down to the footboard
for s in (-1, 1):
    pts = [(BX0 + 0.02, s * 0.66, 1.54), (1.62, s * 0.68, 1.60),
           (1.95, s * 0.64, 1.52), (2.16, s * 0.56, 1.30), (2.24, s * 0.46, 1.06)]
    sweep(bm, pts, rect_profile(0.30, 0.055, corner=0.020))
box = bm_obj(bm, "Box.Frame", C_BODY, smooth=False)
assign(box, M_LACQ)
bevel_obj(box, width=0.010, segments=2)

# footboard / dashboard
bm = new_bm()
pts = [(2.10, 0.0, 1.44), (2.28, 0.0, 1.20), (2.34, 0.0, 0.96)]
rings2 = []
for p in pts:
    rings2.append([(p[0] - 0.03, -0.60, p[2]), (p[0] + 0.03, -0.60, p[2]),
                   (p[0] + 0.03, 0.60, p[2]), (p[0] - 0.03, 0.60, p[2])])
loft(bm, rings2, close_loop=True, cap_ends=True)
dash = bm_obj(bm, "Box.Dashboard", C_BODY, smooth=False)
assign(dash, M_LACQ)
bevel_obj(dash, width=0.010, segments=2)

# seat: leather cushion, buttoned back
bm = new_bm()
sphere(bm, (1.70, 0.0, SEAT_Z - 0.055), 1.0, segments=20, rings=12,
       scale=(0.34, 0.62, 0.11))
seat = bm_obj(bm, "Box.Cushion", C_DET, smooth=True)
assign(seat, M_LEATHER)

bm = new_bm()
back_rings = []
for i in range(13):
    t = i / 12.0
    z = SEAT_Z + 0.02 + 0.50 * t
    x = 1.36 - 0.10 * math.sin(t * math.pi * 0.8)
    hw = 0.60 - 0.06 * t * t
    back_rings.append([(x - 0.05, -hw, z), (x + 0.07, -hw, z),
                       (x + 0.07, hw, z), (x - 0.05, hw, z)])
loft(bm, back_rings, close_loop=True, cap_ends=True)
back = bm_obj(bm, "Box.Backrest", C_DET, smooth=True)
assign(back, M_LEATHER)
bevel_obj(back, width=0.010, segments=2)

# buttons on the backrest
bm = new_bm()
for i in range(3):
    for j in range(4):
        z = SEAT_Z + 0.14 + i * 0.145
        y = -0.42 + j * 0.28
        sphere(bm, (1.325 - 0.06 * math.sin((i / 3.0) * math.pi * 0.8), y, z), 0.018,
               segments=10, rings=6)
buttons = bm_obj(bm, "Box.Buttons", C_DET, smooth=True)
assign(buttons, M_BRASS)

# hammercloth valance hanging off the box
bm = new_bm()
val_rings = []
for i in range(17):
    t = i / 16.0
    z = 1.50 - 0.34 * t
    fold = 0.012 * math.sin(t * 8.0)
    ring = []
    NPT = 28
    for j in range(NPT):
        a = TAU * j / NPT
        cu, su = math.cos(a), math.sin(a)
        u = math.copysign(abs(cu) ** (2.0 / 5.0), cu)
        v = math.copysign(abs(su) ** (2.0 / 5.0), su)
        ring.append(((BX0 + BX1) * 0.5 + (BX1 - BX0) * 0.5 * u * (1.0 + fold),
                     0.70 * v * (1.0 + fold), z))
    val_rings.append(ring)
loft(bm, val_rings, close_loop=True, cap_ends=False)
valance = bm_obj(bm, "Box.Hammercloth", C_LACQ if False else C_DET, smooth=True)
assign(valance, bpy.data.materials["Velvet.Crimson"])
solidify(valance, thickness=0.012, offset=0.0)

# iron brackets carrying the box off the body
bm = new_bm()
for s in (-1, 1):
    sweep(bm, [(X1 - 0.10, s * 0.60, floor_z(X1 - 0.10) + 0.10),
               (1.52, s * 0.62, 1.47), (1.95, s * 0.58, 1.46)],
          rect_profile(0.045, 0.030, corner=0.008))
    sweep(bm, [(1.62, s * 0.64, 1.47), (1.60, s * 0.60, 1.10),
               (GEO["front_x"] + 0.10, s * 0.50, GEO["front_axle_z"] + 0.34)],
          rect_profile(0.032, 0.028, corner=0.006))
brk = bm_obj(bm, "Box.Brackets", C_DET, smooth=True)
assign(brk, M_IRON)

# whip socket and rein rail
bm = new_bm()
cyl(bm, (2.00, -0.58, 1.66), 0.030, 0.26, segments=12, rot=(math.radians(-14), 0, 0))
sweep(bm, [(2.20, -0.46, 1.30), (2.24, 0.0, 1.34), (2.20, 0.46, 1.30)],
      rect_profile(0.022, 0.022, corner=0.008))
rail2 = bm_obj(bm, "Box.Fittings", C_DET, smooth=True)
assign(rail2, M_BRASS)

# ---------------------------------------------------------------- rear platform
bm = new_bm()
bbox(bm, (X0 - 0.30, 0.0, 1.16), (0.62, 1.10, 0.07))
for s in (-1, 1):
    sweep(bm, [(X0 - 0.02, s * 0.50, floor_z(X0 - 0.02) - 0.02),
               (X0 - 0.34, s * 0.52, 1.14)], rect_profile(0.055, 0.045, corner=0.010))
plat = bm_obj(bm, "Rear.Platform", C_DET, smooth=False)
assign(plat, M_EBONY)
bevel_obj(plat, width=0.008, segments=2)

bm = new_bm()
bbox(bm, (X0 - 0.32, 0.0, 1.42), (0.52, 0.92, 0.44))
chest = bm_obj(bm, "Rear.Chest", C_DET, smooth=False)
assign(chest, M_TAN)
bevel_obj(chest, width=0.024, segments=3)

bm = new_bm()
for dy in (-0.30, 0.30):
    sweep(bm, [(X0 - 0.58, dy, 1.62), (X0 - 0.06, dy, 1.62),
               (X0 - 0.06, dy, 1.22)], rect_profile(0.012, 0.070, corner=0.004))
chest_straps = bm_obj(bm, "Rear.ChestStraps", C_DET, smooth=True)
assign(chest_straps, M_LEATHER)

__result__ = {"built": ["Body.Roof", "Roof.Rail", "Roof.Trunk", "Box.Frame",
                        "Box.Cushion", "Box.Backrest", "Box.Hammercloth",
                        "Rear.Platform", "Rear.Chest"],
              "roof_top_mid": round(roof_top(0.0), 3)}
print(__result__)
