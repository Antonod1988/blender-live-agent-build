import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())

C_DET = get_coll("Details", get_coll("Carriage"))
C_GEAR = get_coll("Undercarriage", get_coll("Carriage"))
GEO = bpy.app.driver_namespace["geo"]

M_OAK = bpy.data.materials["Wood.Oak"]
M_EBONY = bpy.data.materials["Wood.Ebony"]
M_IRON = bpy.data.materials["Iron.Black"]
M_BRASS = bpy.data.materials["Brass.Fittings"]
M_GOLD = bpy.data.materials["Gold.Ornament"]
M_LEATHER = bpy.data.materials["Leather.Black"]
M_ROPE = bpy.data.materials["Rope.Hemp"]
M_CRYSTAL = bpy.data.materials["Crystal.Arcane"]

FX = GEO["front_x"]
AZ = GEO["front_axle_z"]

# ---- lanterns: drop them to the body corners and shrink the door sigil -----
for nm in ("L", "R"):
    for suffix in ("Frame", "Glass", "Flame", "Bracket"):
        ob = bpy.data.objects.get("Lantern.%s.%s" % (nm, suffix))
        if ob:
            ob.location.z -= 0.17
            ob.location.x -= 0.03
    lo = bpy.data.objects.get("LanternLight.%s" % nm)
    if lo:
        lo.location.z -= 0.17
        lo.location.x -= 0.03
sig = bpy.data.objects.get("Door.Sigil")
if sig:
    sig.scale = (0.42, 0.42, 0.42)

# ---------------------------------------------------------------- splinter bar
bm = new_bm()
SB_X, SB_Z = 2.34, 0.60
rows = []
for i in range(13):
    t = -1.0 + 2.0 * i / 12
    y = t * 0.86
    z = SB_Z + 0.035 * (1.0 - t * t)
    rows.append([(SB_X - 0.055, y, z - 0.055), (SB_X + 0.055, y, z - 0.055),
                 (SB_X + 0.055, y, z + 0.055), (SB_X - 0.055, y, z + 0.055)])
loft(bm, rows, close_loop=True, cap_ends=True)
sb = bm_obj(bm, "Harness.SplinterBar", C_GEAR, smooth=False)
assign(sb, M_OAK)
bevel_obj(sb, width=0.008, segments=2)

bm = new_bm()
for y in (-0.86, -0.44, 0.0, 0.44, 0.86):
    z = SB_Z + 0.035 * (1.0 - (y / 0.86) ** 2)
    bbox(bm, (SB_X, y, z), (0.125, 0.055, 0.125))
for s in (-1, 1):
    # stays back to the axle bed
    sweep(bm, [(SB_X - 0.02, s * 0.80, SB_Z + 0.02), (FX + 0.30, s * 0.55, AZ + 0.20),
               (FX + 0.05, s * 0.34, AZ + 0.16)], rect_profile(0.030, 0.026, corner=0.006))
sbi = bm_obj(bm, "Harness.SplinterIron", C_GEAR, smooth=True)
assign(sbi, M_IRON)
bevel_obj(sbi, width=0.004, segments=2)

# ---------------------------------------------------------------- pole
bm = new_bm()
pole_pts = []
for i in range(25):
    t = i / 24.0
    x = 2.02 + t * 2.76
    z = 0.545 + 0.16 * t * t
    pole_pts.append((x, 0.0, z))
sweep(bm, pole_pts, rect_profile(0.115, 0.115, corner=0.048),
      scale=lambda t: 1.0 - 0.42 * t)
pole = bm_obj(bm, "Harness.Pole", C_OAK if False else C_GEAR, smooth=True)
assign(pole, M_OAK)

bm = new_bm()
# iron ferrules along the pole
for t, r in ((0.02, 0.062), (0.34, 0.052), (0.68, 0.043), (0.97, 0.035)):
    i = int(t * 24)
    p = pole_pts[i]
    cyl(bm, p, r + 0.008, 0.055, axis="X", segments=16)
# pole head: ring, hook and a warding crystal
tip = pole_pts[-1]
revolve(bm, [(0.052, -0.012), (0.082, -0.012), (0.082, 0.012), (0.052, 0.012),
             (0.052, -0.012)], segments=20)
bmesh.ops.translate(bm, verts=[v for v in bm.verts if abs(v.co.x) < 0.2],
                    vec=Vector((tip[0] + 0.03, 0.0, tip[2])))
for a0 in (math.radians(200), math.radians(340)):
    hook = arc_path((tip[0] + 0.10, 0.0, tip[2] - 0.075), 0.075, a0, a0 + math.radians(210), 14,
                    plane="XZ")
    sweep(bm, hook, rect_profile(0.020, 0.020, corner=0.007))
pi_ = bm_obj(bm, "Harness.PoleIron", C_GEAR, smooth=True)
assign(pi_, M_IRON)

bm = new_bm()
sphere(bm, (tip[0] + 0.13, 0.0, tip[2] + 0.055), 1.0, segments=14, rings=8,
       scale=(0.052, 0.052, 0.075))
gem = bm_obj(bm, "Harness.PoleGem", C_DET, smooth=True)
assign(gem, M_CRYSTAL)

gl = bpy.data.lights.new("PoleGemLight", "POINT")
gl.energy = 12.0
gl.color = (0.35, 0.62, 1.0)
gl.shadow_soft_size = 0.05
glo = bpy.data.objects.new("PoleGemLight", gl)
glo.location = (tip[0] + 0.13, 0.0, tip[2] + 0.06)
link(glo, C_DET)

# ---------------------------------------------------------------- swingletrees
bm = new_bm()
for s in (-1, 1):
    y0 = s * 0.46
    rows = []
    for i in range(11):
        t = -1.0 + 2.0 * i / 10
        rows.append([(2.46 - 0.042, y0 + t * 0.34, 0.545 - 0.032 * (1 - t * t) - 0.036),
                     (2.46 + 0.042, y0 + t * 0.34, 0.545 - 0.032 * (1 - t * t) - 0.036),
                     (2.46 + 0.042, y0 + t * 0.34, 0.545 - 0.032 * (1 - t * t) + 0.036),
                     (2.46 - 0.042, y0 + t * 0.34, 0.545 - 0.032 * (1 - t * t) + 0.036)])
    loft(bm, rows, close_loop=True, cap_ends=True)
sw = bm_obj(bm, "Harness.Swingletrees", C_GEAR, smooth=False)
assign(sw, M_EBONY)
bevel_obj(sw, width=0.010, segments=2)

bm = new_bm()
for s in (-1, 1):
    y0 = s * 0.46
    for t in (-1.0, 0.0, 1.0):
        y = y0 + t * 0.34
        z = 0.545 - 0.032 * (1 - t * t)
        bbox(bm, (2.46, y, z), (0.10, 0.045, 0.10))
        if abs(t) > 0.5:
            hook = arc_path((2.52, y, z - 0.02), 0.055, math.radians(-60), math.radians(200), 12,
                            plane="XZ")
            hook = [(p[0], y, p[2]) for p in hook]
            sweep(bm, hook, rect_profile(0.016, 0.016, corner=0.005))
    # link up to the splinter bar
    sweep(bm, [(2.46, y0, 0.545 + 0.05), (SB_X + 0.02, y0, SB_Z + 0.04)],
          rect_profile(0.026, 0.022, corner=0.006))
swi = bm_obj(bm, "Harness.SwingletreeIron", C_GEAR, smooth=True)
assign(swi, M_IRON)

# ---------------------------------------------------------------- traces & chains
bm = new_bm()
for s in (-1, 1):
    for dy in (-0.34, 0.34):
        y = s * 0.46 + dy
        pts = [(2.52, y, 0.53), (3.10, y * 0.86, 0.60), (3.75, y * 0.70, 0.70),
               (4.35, y * 0.58, 0.80)]
        sweep(bm, pts, rect_profile(0.010, 0.055, corner=0.003))
traces = bm_obj(bm, "Harness.Traces", C_DET, smooth=True)
assign(traces, M_LEATHER)

bm = new_bm()
for s in (-1, 1):
    pts = [(2.40, s * 0.86, SB_Z), (2.90, s * 0.72, 0.50), (3.40, s * 0.55, 0.56)]
    sweep(bm, pts, rect_profile(0.016, 0.016, corner=0.006))
chains = bm_obj(bm, "Harness.Chains", C_DET, smooth=True)
assign(chains, M_IRON)

# ---------------------------------------------------------------- coachman's whip
bm = new_bm()
whip = []
for i in range(19):
    t = i / 18.0
    whip.append((2.00 - 0.10 * t, -0.58 - 0.28 * t, 1.66 + 1.05 * t - 0.22 * t * t))
sweep(bm, whip, rect_profile(0.017, 0.017, corner=0.007), scale=lambda t: 1.0 - 0.72 * t)
wh = bm_obj(bm, "Box.Whip", C_DET, smooth=True)
assign(wh, M_EBONY)

bm = new_bm()
lash = []
for i in range(16):
    t = i / 15.0
    lash.append((1.90 - 0.10 * t - 0.35 * t * t, -0.86 - 0.10 * t,
                 2.49 - 0.30 * t - 0.55 * t * t))
sweep(bm, lash, rect_profile(0.008, 0.008, corner=0.003), scale=lambda t: 1.0 - 0.5 * t)
ls = bm_obj(bm, "Box.WhipLash", C_DET, smooth=True)
assign(ls, M_LEATHER)

__result__ = {"built": ["Harness.SplinterBar", "Harness.Pole", "Harness.Swingletrees",
                        "Harness.Traces", "Harness.PoleGem", "Box.Whip"],
              "pole_tip": pole_pts[-1]}
print(__result__)
