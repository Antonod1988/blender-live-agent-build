import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())

C_GEAR = get_coll("Undercarriage", get_coll("Carriage"))
GEO = bpy.app.driver_namespace["geo"]
M_IRON = bpy.data.materials["Iron.Black"]
M_BRASS = bpy.data.materials["Brass.Fittings"]

for n in ("Turntable.Lower", "Turntable.Upper"):
    ob = bpy.data.objects.get(n)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)

FX = GEO["front_x"]
tz = GEO["front_axle_z"] + 0.16

# lower ring (bolted to the axle bed) --------------------------------------
bm = new_bm()
revolve(bm, [(0.115, tz - 0.030), (0.300, tz - 0.030), (0.312, tz - 0.014),
             (0.300, tz + 0.002), (0.115, tz + 0.002), (0.115, tz - 0.030)],
        segments=48)
for i in range(8):
    a = TAU * i / 8
    cyl(bm, (math.cos(a) * 0.268, math.sin(a) * 0.268, tz - 0.006), 0.016, 0.026, segments=8)
bmesh.ops.translate(bm, verts=bm.verts[:], vec=Vector((FX, 0.0, 0.0)))
low = bm_obj(bm, "Turntable.Lower", C_GEAR, smooth=True)
assign(low, M_IRON)

# upper ring + king pin (carries the body frame) ---------------------------
bm = new_bm()
revolve(bm, [(0.100, tz + 0.006), (0.278, tz + 0.006), (0.288, tz + 0.022),
             (0.278, tz + 0.038), (0.100, tz + 0.038), (0.100, tz + 0.006)],
        segments=48)
cyl(bm, (0.0, 0.0, tz + 0.070), 0.040, 0.180, segments=20)
revolve(bm, [(0.0, tz + 0.158), (0.062, tz + 0.158), (0.068, tz + 0.176),
             (0.040, tz + 0.196), (0.0, tz + 0.200)], segments=24)
bmesh.ops.translate(bm, verts=bm.verts[:], vec=Vector((FX, 0.0, 0.0)))
up = bm_obj(bm, "Turntable.Upper", C_GEAR, smooth=True)
assign(up, M_IRON)

# brass wear ring so the joint reads as a bearing ---------------------------
bm = new_bm()
revolve(bm, [(0.290, tz + 0.000), (0.306, tz + 0.000), (0.306, tz + 0.010),
             (0.290, tz + 0.010), (0.290, tz + 0.000)], segments=48)
bmesh.ops.translate(bm, verts=bm.verts[:], vec=Vector((FX, 0.0, 0.0)))
ring = bm_obj(bm, "Turntable.WearRing", C_GEAR, smooth=True)
assign(ring, M_BRASS)

__result__ = {"rebuilt": ["Turntable.Lower", "Turntable.Upper", "Turntable.WearRing"],
              "z": tz}
print(__result__)
