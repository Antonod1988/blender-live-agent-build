import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())

C_BODY = get_coll("Body", get_coll("Carriage"))
C_DET = get_coll("Details", get_coll("Carriage"))
GEO = bpy.app.driver_namespace["geo"]
B = bpy.app.driver_namespace["body"]
X1, floor_z = B["x1"], B["floor_z"]

M_LACQ = bpy.data.materials["Lacquer.Burgundy"]
M_BLACK = bpy.data.materials["Lacquer.Black"]
M_GOLD = bpy.data.materials["Gold.Ornament"]
M_IRON = bpy.data.materials["Iron.Black"]
M_OAK = bpy.data.materials["Wood.Oak"]

for n in ("Box.Frame", "Box.Dashboard"):
    ob = bpy.data.objects.get(n)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)


def plate(bm, outline_xz, y0, y1):
    """Extrude a closed XZ outline between two Y planes."""
    a = [(x, y0, z) for x, z in outline_xz]
    b = [(x, y1, z) for x, z in outline_xz]
    loft(bm, [a, b], close_loop=True, cap_ends=True)


FLOOR_BOX = 1.545
bm = new_bm()
# box floor
bbox(bm, (1.70, 0.0, FLOOR_BOX - 0.038), (0.90, 1.28, 0.075))
# swooping side cheeks (thin vertical plates, hooking down to the footboard)
cheek = [
    (1.26, 1.72), (1.62, 1.76), (1.96, 1.70), (2.14, 1.52),
    (2.24, 1.24), (2.30, 1.04), (2.19, 1.01), (2.13, 1.22),
    (2.02, 1.42), (1.90, 1.50), (1.62, 1.55), (1.26, 1.52),
]
for s in (-1, 1):
    plate(bm, cheek, s * 0.615, s * 0.670)
# front riser under the seat
plate(bm, [(2.02, 1.50), (2.10, 1.50), (2.14, 1.06), (2.06, 1.05)], -0.62, 0.62)
box = bm_obj(bm, "Box.Frame", C_BODY, smooth=False)
assign(box, M_LACQ)
bevel_obj(box, width=0.008, segments=2)

# footboard: a slatted board angled down in front of the driver
bm = new_bm()
for i in range(5):
    x0 = 2.14 + i * 0.045
    z0 = 1.30 - i * 0.062
    plate(bm, [(x0, z0), (x0 + 0.040, z0 - 0.006), (x0 + 0.036, z0 - 0.052),
               (x0 - 0.004, z0 - 0.046)], -0.55, 0.55)
foot = bm_obj(bm, "Box.Footboard", C_BODY, smooth=False)
assign(foot, M_OAK)
bevel_obj(foot, width=0.004, segments=2)

# dashboard: a lacquered splash-board with a gold rim
bm = new_bm()
plate(bm, [(2.30, 1.06), (2.345, 1.05), (2.40, 1.44), (2.355, 1.455)], -0.58, 0.58)
dash = bm_obj(bm, "Box.Dashboard", C_BODY, smooth=False)
assign(dash, M_BLACK)
bevel_obj(dash, width=0.008, segments=2)

bm = new_bm()
sweep(bm, [(2.375, -0.58, 1.455), (2.385, 0.0, 1.468), (2.375, 0.58, 1.455)],
      rect_profile(0.026, 0.022, corner=0.008))
for s in (-1, 1):
    sweep(bm, [(2.30, s * 0.58, 1.06), (2.375, s * 0.585, 1.45)],
          rect_profile(0.020, 0.018, corner=0.006))
dashtrim = bm_obj(bm, "Box.DashTrim", C_DET, smooth=True)
assign(dashtrim, M_GOLD)

# iron step irons for climbing to the box
bm = new_bm()
for s in (-1, 1):
    sweep(bm, [(1.96, s * 0.70, 1.44), (2.02, s * 0.80, 1.16),
               (1.98, s * 0.78, 0.94)], rect_profile(0.030, 0.024, corner=0.006))
    bbox(bm, (1.99, s * 0.79, 0.94), (0.20, 0.11, 0.020))
    bbox(bm, (2.00, s * 0.79, 1.19), (0.18, 0.10, 0.018))
steps = bm_obj(bm, "Box.StepIrons", C_DET, smooth=True)
assign(steps, M_IRON)
bevel_obj(steps, width=0.004, segments=2)

__result__ = {"rebuilt": ["Box.Frame", "Box.Footboard", "Box.Dashboard",
                          "Box.DashTrim", "Box.StepIrons"]}
print(__result__)
