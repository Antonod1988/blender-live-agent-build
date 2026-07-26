import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())

C_DET = get_coll("Details", get_coll("Carriage"))
B = bpy.app.driver_namespace["body"]
surf, normal_at, v_to_t = B["surf"], B["normal"], B["v_to_t"]

M_FLAME = bpy.data.materials["Flame.Core"]
M_CRYSTAL = bpy.data.materials["Crystal.Arcane"]

for n in ("Door.Sigil", "Lantern.L.Flame", "Lantern.R.Flame", "Harness.PoleGem"):
    ob = bpy.data.objects.get(n)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)

# --- door sigils, sunk into the shield ------------------------------------
bm = new_bm()
for side in (1, -1):
    t = v_to_t(-0.30)
    p, n = surf(-0.19, t), normal_at(-0.19, t)
    if side < 0:
        p, n = Vector((p.x, -p.y, p.z)), Vector((n.x, -n.y, n.z))
    c = p + n * 0.030
    sphere(bm, tuple(c), 1.0, segments=14, rings=9, scale=(0.030, 0.030, 0.030))
sig = bm_obj(bm, "Door.Sigil", C_DET, smooth=True)
assign(sig, M_CRYSTAL)

# --- lantern candles and flames -------------------------------------------
for nm, side in (("L", 1), ("R", -1)):
    bm = new_bm()
    base = Vector((1.205, side * 0.735, 1.85))
    cyl(bm, tuple(base + Vector((0, 0, -0.055))), 0.020, 0.115, segments=10)
    sphere(bm, tuple(base + Vector((0, 0, 0.040))), 1.0, segments=12, rings=9,
           scale=(0.017, 0.017, 0.042))
    ob = bm_obj(bm, "Lantern.%s.Flame" % nm, C_DET, smooth=True)
    assign(ob, M_FLAME)

# --- pole gem --------------------------------------------------------------
bm = new_bm()
gemc = Vector((4.91, 0.0, 0.762))
sphere(bm, tuple(gemc), 1.0, segments=16, rings=10, scale=(0.045, 0.045, 0.068))
gem = bm_obj(bm, "Harness.PoleGem", C_DET, smooth=True)
assign(gem, M_CRYSTAL)

gl = bpy.data.objects.get("PoleGemLight")
if gl:
    gl.location = tuple(gemc)

# --- audit: nothing else should carry a stray object scale ----------------
stray = {o.name: tuple(round(v, 3) for v in o.scale)
         for o in bpy.data.objects
         if any(abs(v - 1.0) > 1e-3 for v in o.scale) and o.type in {"MESH", "EMPTY"}}

__result__ = {"rebuilt": ["Door.Sigil", "Lantern.L.Flame", "Lantern.R.Flame",
                          "Harness.PoleGem"],
              "stray_scales": stray}
print(__result__)
