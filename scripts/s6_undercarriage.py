import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())

C_GEAR = get_coll("Undercarriage", get_coll("Carriage"))

M_IRON = bpy.data.materials["Iron.Black"]
M_STEEL = bpy.data.materials["Steel.Spring"]
M_OAK = bpy.data.materials["Wood.Oak"]
M_EBONY = bpy.data.materials["Wood.Ebony"]
M_GOLD = bpy.data.materials["Gold.Ornament"]
M_LEATHER = bpy.data.materials["Leather.Black"]
M_BRASS = bpy.data.materials["Brass.Fittings"]

# key chassis datums, shared with later stages
GEO = {
    "rear_x": -1.14, "front_x": 1.46,
    "rear_axle_z": 0.630, "front_axle_z": 0.387,
    "track_rear": 0.98, "track_front": 0.92,
    "floor_z": 1.13, "roof_z": 2.44,
    "body_x0": -1.88, "body_x1": 0.72, "body_hw": 0.80,
    "box_x1": 1.78,
}
bpy.app.driver_namespace["geo"] = GEO

parts = []


def add(bm, name, material, smooth=False, bevel=None):
    ob = bm_obj(bm, name, C_GEAR, smooth=smooth)
    assign(ob, material)
    if bevel:
        bevel_obj(ob, width=bevel, segments=2)
    parts.append(ob)
    return ob


# ---------------------------------------------------------------- axles
bm = new_bm()
# rear axle tree: squared timber centre, round iron arms
bbox(bm, (GEO["rear_x"], 0.0, GEO["rear_axle_z"]), (0.16, 1.52, 0.15))
for s in (-1, 1):
    bbox(bm, (GEO["rear_x"], s * 0.80, GEO["rear_axle_z"]), (0.14, 0.10, 0.13))
add(bm, "Axle.RearTree", M_OAK, bevel=0.012)

bm = new_bm()
for s in (-1, 1):
    cone(bm, (GEO["rear_x"], s * 0.905, GEO["rear_axle_z"]), 0.062, 0.048, 0.30,
         axis="Y", segments=16)
    # collar and linchpin
    cyl(bm, (GEO["rear_x"], s * 1.052, GEO["rear_axle_z"]), 0.052, 0.030, axis="Y", segments=16)
    cyl(bm, (GEO["rear_x"], s * 1.075, GEO["rear_axle_z"] + 0.035), 0.010, 0.075,
        axis="Z", segments=8)
    # iron strap wrapping the timber
    for dx in (-0.055, 0.055):
        bbox(bm, (GEO["rear_x"] + dx, s * 0.45, GEO["rear_axle_z"]), (0.018, 0.11, 0.175))
add(bm, "Axle.RearIron", M_IRON, smooth=True, bevel=0.005)

bm = new_bm()
bbox(bm, (GEO["front_x"], 0.0, GEO["front_axle_z"]), (0.15, 1.42, 0.135))
for s in (-1, 1):
    bbox(bm, (GEO["front_x"], s * 0.76, GEO["front_axle_z"]), (0.13, 0.09, 0.12))
add(bm, "Axle.FrontTree", M_OAK, bevel=0.012)

bm = new_bm()
for s in (-1, 1):
    cone(bm, (GEO["front_x"], s * 0.855, GEO["front_axle_z"]), 0.056, 0.044, 0.28,
         axis="Y", segments=16)
    cyl(bm, (GEO["front_x"], s * 0.992, GEO["front_axle_z"]), 0.047, 0.028, axis="Y", segments=16)
    cyl(bm, (GEO["front_x"], s * 1.012, GEO["front_axle_z"] + 0.032), 0.009, 0.070,
        axis="Z", segments=8)
add(bm, "Axle.FrontIron", M_IRON, smooth=True, bevel=0.005)

# ---------------------------------------------------------------- turntable
bm = new_bm()
tz = GEO["front_axle_z"] + 0.16
revolve(bm, [(0.0, tz - 0.020), (0.30, tz - 0.020), (0.31, tz - 0.008),
             (0.30, tz + 0.004), (0.0, tz + 0.004)], segments=40,
        center=(GEO["front_x"], 0, 0))
for v in bm.verts:
    v.co.x += GEO["front_x"]
add(bm, "Turntable.Lower", M_IRON, smooth=True)

bm = new_bm()
revolve(bm, [(0.0, tz + 0.010), (0.27, tz + 0.010), (0.285, 0.022 + tz),
             (0.27, tz + 0.034), (0.0, tz + 0.034)], segments=40)
for v in bm.verts:
    v.co.x += GEO["front_x"]
# king pin
cyl(bm, (GEO["front_x"], 0.0, tz + 0.06), 0.038, 0.16, segments=16)
add(bm, "Turntable.Upper", M_IRON, smooth=True)

# futchells: the forked arms that carry the pole socket
bm = new_bm()
for s in (-1, 1):
    p = [(GEO["front_x"] - 0.05, s * 0.10, GEO["front_axle_z"] + 0.10),
         (GEO["front_x"] + 0.30, s * 0.16, GEO["front_axle_z"] + 0.115),
         (GEO["front_x"] + 0.62, s * 0.13, GEO["front_axle_z"] + 0.10)]
    sweep(bm, p, rect_profile(0.075, 0.065, corner=0.012))
add(bm, "Futchells", M_OAK, bevel=0.008)

# ---------------------------------------------------------------- perch beam
bm = new_bm()
perch = [
    (GEO["rear_x"] - 0.05, 0.0, GEO["rear_axle_z"] + 0.02),
    (GEO["rear_x"] + 0.45, 0.0, GEO["rear_axle_z"] - 0.06),
    (0.10, 0.0, 0.470),
    (0.80, 0.0, 0.470),
    (GEO["front_x"] - 0.22, 0.0, tz - 0.03),
    (GEO["front_x"] + 0.02, 0.0, tz - 0.02),
]
sweep(bm, perch, rect_profile(0.115, 0.095, corner=0.020))
add(bm, "Perch", M_OAK, bevel=0.010)

bm = new_bm()
# iron plates and bolts along the perch
for t, ln in ((0.16, 0.16), (0.5, 0.14), (0.86, 0.16)):
    i = int(t * (len(perch) - 1))
    p = Vector(perch[i])
    bbox(bm, (p.x, 0.0, p.z), (ln, 0.135, 0.115))
for s in (-1, 1):
    # stays from the perch up to the rear axle
    a = Vector((GEO["rear_x"] + 0.04, s * 0.06, GEO["rear_axle_z"] - 0.02))
    b = Vector((GEO["rear_x"] + 0.60, s * 0.30, 0.46))
    sweep(bm, [a, (a + b) / 2, b], rect_profile(0.032, 0.055, corner=0.008))
add(bm, "Perch.Ironwork", M_IRON, smooth=True, bevel=0.004)

# ---------------------------------------------------------------- rear C-springs
bm = new_bm()
CX, CZ, CR = GEO["rear_x"] - 0.34, 0.965, 0.352
for s in (-1, 1):
    for leaf, (rr, span, thick) in enumerate((
            (CR, 86.0, 0.019), (CR - 0.020, 74.0, 0.016), (CR - 0.038, 60.0, 0.013))):
        path = arc_path((CX, 0.0, CZ), rr, math.radians(-span), math.radians(span), 26,
                        plane="XZ", y=s * 0.86)
        sweep(bm, path, rect_profile(thick, 0.070 - leaf * 0.008, corner=0.004),
              up=(0.0, 1.0, 0.0))
add(bm, "Spring.RearC", M_STEEL, smooth=True, bevel=0.003)

bm = new_bm()
for s in (-1, 1):
    # spring shackles top and bottom
    for a in (math.radians(-86.0), math.radians(86.0)):
        p = (CX + math.cos(a) * CR, s * 0.86, CZ + math.sin(a) * CR)
        bbox(bm, p, (0.075, 0.105, 0.075))
        cyl(bm, p, 0.020, 0.13, axis="Y", segments=12)
    # clamp at the crown of the C
    bbox(bm, (CX + CR - 0.01, s * 0.86, CZ), (0.07, 0.115, 0.10))
add(bm, "Spring.RearFittings", M_IRON, smooth=True, bevel=0.005)

# ---------------------------------------------------------------- front springs
bm = new_bm()
FX, FZ = GEO["front_x"], GEO["front_axle_z"] + 0.10
for s in (-1, 1):
    for leaf, (rise, half, thick) in enumerate((
            (0.20, 0.42, 0.018), (0.165, 0.35, 0.015), (0.13, 0.28, 0.013))):
        path = []
        for i in range(21):
            t = -1.0 + 2.0 * i / 20
            path.append((FX + t * half, s * 0.62, FZ + rise * (1.0 - t * t)))
        sweep(bm, path, rect_profile(thick, 0.075 - leaf * 0.009, corner=0.004),
              up=(0.0, 1.0, 0.0))
add(bm, "Spring.Front", M_STEEL, smooth=True, bevel=0.003)

bm = new_bm()
for s in (-1, 1):
    bbox(bm, (FX, s * 0.62, FZ + 0.185), (0.085, 0.115, 0.075))
    for dx in (-0.42, 0.42):
        bbox(bm, (FX + dx, s * 0.62, FZ + 0.01), (0.075, 0.10, 0.085))
    # link down to the axle tree
    sweep(bm, [(FX - 0.05, s * 0.62, FZ - 0.02), (FX - 0.02, s * 0.30, GEO["front_axle_z"] + 0.02)],
          rect_profile(0.045, 0.045, corner=0.008))
add(bm, "Spring.FrontFittings", M_IRON, smooth=True, bevel=0.005)

# ---------------------------------------------------------------- leather braces
bm = new_bm()
for s in (-1, 1):
    top = Vector((CX + math.cos(math.radians(86.0)) * CR, s * 0.86,
                  CZ + math.sin(math.radians(86.0)) * CR))
    body = Vector((GEO["body_x0"] + 0.28, s * 0.74, GEO["floor_z"] + 0.10))
    mid = (top + body) * 0.5 + Vector((0.02, 0.0, -0.045))
    sweep(bm, [top, mid, body], rect_profile(0.020, 0.105, corner=0.006))
add(bm, "Brace.RearLeather", M_LEATHER, smooth=True, bevel=0.004)

__result__ = {"parts": [p.name for p in parts], "geo": GEO}
print(__result__)
