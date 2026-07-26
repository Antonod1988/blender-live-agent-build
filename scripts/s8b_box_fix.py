import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())

C_DET = get_coll("Details", get_coll("Carriage"))
GEO = bpy.app.driver_namespace["geo"]
B = bpy.app.driver_namespace["body"]
X1 = B["x1"]

M_LEATHER = bpy.data.materials["Leather.Black"]
M_VELVET = bpy.data.materials["Velvet.Crimson"]
M_GOLD = bpy.data.materials["Gold.Ornament"]
M_BRASS = bpy.data.materials["Brass.Fittings"]

# leather: darker and rougher so it stops mirroring the sky
lb = M_LEATHER.node_tree.nodes["Principled BSDF"]
lb.inputs["Base Color"].default_value = (0.021, 0.019, 0.019, 1.0)
lb.inputs["Roughness"].default_value = 0.66
lb.inputs["Specular IOR Level"].default_value = 0.30
vb = M_VELVET.node_tree.nodes["Principled BSDF"]
vb.inputs["Base Color"].default_value = (0.115, 0.011, 0.024, 1.0)
vb.inputs["Roughness"].default_value = 0.92

# calmer fill so the coachwork keeps its colour
bpy.data.objects["SkyFill"].data.energy = 150.0

for n in ("Box.Cushion", "Box.Backrest", "Box.Buttons", "Box.Hammercloth"):
    ob = bpy.data.objects.get(n)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)

FLOOR_BOX = 1.545
BX0, BX1 = X1 - 0.02, 2.14

# --- cushion sitting on the box floor --------------------------------------
bm = new_bm()
sphere(bm, (1.66, 0.0, FLOOR_BOX + 0.085), 1.0, segments=22, rings=12,
       scale=(0.30, 0.58, 0.095))
# seam roll along the front edge
sweep(bm, [(1.96, -0.56, FLOOR_BOX + 0.075), (1.96, 0.0, FLOOR_BOX + 0.082),
           (1.96, 0.56, FLOOR_BOX + 0.075)],
      rect_profile(0.055, 0.055, corner=0.020))
cushion = bm_obj(bm, "Box.Cushion", C_DET, smooth=True)
assign(cushion, M_LEATHER)

# --- backrest: modest, tucked against the body front -----------------------
bm = new_bm()
rings = []
for i in range(11):
    t = i / 10.0
    z = FLOOR_BOX + 0.16 + 0.40 * t
    x = 1.335 - 0.075 * math.sin(t * math.pi * 0.75)
    hw = 0.50 - 0.055 * t * t
    rings.append([(x - 0.045, -hw, z), (x + 0.055, -hw, z),
                  (x + 0.055, hw, z), (x - 0.045, hw, z)])
loft(bm, rings, close_loop=True, cap_ends=True)
back = bm_obj(bm, "Box.Backrest", C_DET, smooth=True)
assign(back, M_LEATHER)
bevel_obj(back, width=0.012, segments=2)

bm = new_bm()
for i in range(3):
    for j in range(4):
        t = (i + 0.5) / 3.0
        z = FLOOR_BOX + 0.22 + i * 0.135
        y = -0.34 + j * 0.227
        sphere(bm, (1.335 - 0.075 * math.sin(t * math.pi * 0.75) + 0.056, y, z),
               0.016, segments=10, rings=6)
buttons = bm_obj(bm, "Box.Buttons", C_DET, smooth=True)
assign(buttons, M_BRASS)

# --- hammercloth: draped valance with scalloped hem ------------------------
bm = new_bm()
NPT = 56
rows = []
for i in range(13):
    t = i / 12.0
    ring = []
    for j in range(NPT):
        a = TAU * j / NPT
        cu, su = math.cos(a), math.sin(a)
        u = math.copysign(abs(cu) ** (2.0 / 6.0), cu)
        v = math.copysign(abs(su) ** (2.0 / 6.0), su)
        fold = 0.014 * math.sin(a * 9.0) * t
        x = (BX0 + BX1) * 0.5 + ((BX1 - BX0) * 0.5 - 0.02) * u * (1.0 + fold)
        y = 0.655 * v * (1.0 + fold)
        scallop = 0.035 * math.sin(a * 9.0) ** 2
        z = FLOOR_BOX - 0.03 - (0.26 + scallop) * t
        ring.append((x, y, z))
    rows.append(ring)
loft(bm, rows, close_loop=True, cap_ends=False)
val = bm_obj(bm, "Box.Hammercloth", C_DET, smooth=True)
assign(val, M_VELVET)
solidify(val, thickness=0.010, offset=0.0)

# gold fringe and bullion along the hem
bm = new_bm()
hem = rows[-1]
sweep(bm, [tuple(p) for p in hem] + [tuple(hem[0])],
      rect_profile(0.022, 0.016, corner=0.005), caps=False)
for j in range(0, NPT, 2):
    p = hem[j]
    cyl(bm, (p[0], p[1], p[2] - 0.035), 0.006, 0.07, segments=6)
fringe = bm_obj(bm, "Box.Fringe", C_DET, smooth=True)
assign(fringe, M_GOLD)

__result__ = {"fixed": ["Box.Cushion", "Box.Backrest", "Box.Hammercloth", "Box.Fringe"]}
print(__result__)
