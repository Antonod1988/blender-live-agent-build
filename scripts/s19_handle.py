import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())

C_DET = get_coll("Details", get_coll("Carriage"))
B = bpy.app.driver_namespace["body"]
surf, normal_at, v_to_t = B["surf"], B["normal"], B["v_to_t"]
M_BRASS = bpy.data.materials["Brass.Fittings"]

ob = bpy.data.objects.get("Door.Furniture")
if ob:
    bpy.data.objects.remove(ob, do_unlink=True)

HANDLE_X, HANDLE_V = 0.20, 0.02      # clear of the armorial shield
HINGE_X = -0.66

bm = new_bm()
for side in (1, -1):
    t = v_to_t(HANDLE_V)
    p, n = surf(HANDLE_X, t), normal_at(HANDLE_X, t)
    if side < 0:
        p, n = Vector((p.x, -p.y, p.z)), Vector((n.x, -n.y, n.z))
    yaw = math.atan2(n.y, n.x)
    base = p + n * 0.010
    # escutcheon plate
    cyl(bm, tuple(base + n * 0.006), 0.046, 0.014, segments=20, rot=(0.0, math.pi / 2, yaw))
    cyl(bm, tuple(base + n * 0.020), 0.026, 0.028, segments=16, rot=(0.0, math.pi / 2, yaw))
    # lever dropping toward the rear of the door
    up = n.cross(Vector((1.0, 0.0, 0.0)))
    up = -up if up.z < 0 else up
    lever = [tuple(base + n * 0.036),
             tuple(base + n * 0.062 - Vector((0.018, 0.0, 0.0)) - up * 0.022),
             tuple(base + n * 0.058 - Vector((0.048, 0.0, 0.0)) - up * 0.062),
             tuple(base + n * 0.044 - Vector((0.060, 0.0, 0.0)) - up * 0.098)]
    sweep(bm, lever, rect_profile(0.021, 0.018, corner=0.007))
    sphere(bm, lever[-1], 0.021, segments=12, rings=8)
    # hinges on the trailing edge
    for vz in (0.40, -0.36):
        tt = v_to_t(vz)
        hp, hn = surf(HINGE_X, tt), normal_at(HINGE_X, tt)
        if side < 0:
            hp, hn = Vector((hp.x, -hp.y, hp.z)), Vector((hn.x, -hn.y, hn.z))
        cyl(bm, tuple(hp + hn * 0.016), 0.018, 0.105, segments=12,
            rot=(math.radians(90), 0, 0))
        bbox(bm, tuple(hp + hn * 0.008), (0.070, 0.028, 0.050))
furn = bm_obj(bm, "Door.Furniture", C_DET, smooth=True)
assign(furn, M_BRASS)

__result__ = {"handle_at": (HANDLE_X, HANDLE_V)}
print(__result__)
