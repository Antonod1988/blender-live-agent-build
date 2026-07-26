import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())

C_BODY = get_coll("Body", get_coll("Carriage"))
C_GEAR = get_coll("Undercarriage", get_coll("Carriage"))
GEO = bpy.app.driver_namespace["geo"]

M_LACQ = bpy.data.materials["Lacquer.Burgundy"]
M_PANEL = bpy.data.materials["Panel.Inlay"]
M_GOLD = bpy.data.materials["Gold.Ornament"]
M_EBONY = bpy.data.materials["Wood.Ebony"]
M_LEATHER = bpy.data.materials["Leather.Black"]

for n in ("Body.Shell", "Body.Mouldings", "Body.Pillars", "Brace.RearLeather"):
    ob = bpy.data.objects.get(n)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)

# ---------------------------------------------------------------- proportions
X0, X1 = -1.30, 1.28
FLOOR, ROOF = 1.06, 2.36
HW = 0.715
GEO.update({"body_x0": X0, "body_x1": X1, "body_hw": HW,
            "floor_z": FLOOR, "roof_z": ROOF, "box_x1": 2.12})
XC, XH = (X0 + X1) * 0.5, (X1 - X0) * 0.5
NT, NX = 72, 56


def xn_of(x):
    return (x - XC) / XH


def floor_z(x):
    return FLOOR + 0.155 * abs(xn_of(x)) ** 3.0


def roof_z(x):
    return ROOF - 0.055 * xn_of(x) ** 2


def half_w(x):
    return HW * (1.0 - 0.10 * abs(xn_of(x)) ** 3.0)


def end_scale(x):
    """Round the body off in plan view instead of leaving flat slabs."""
    a = abs(xn_of(x))
    if a < 0.84:
        return 1.0
    t = (a - 0.84) / 0.16
    return 1.0 - 0.42 * (t * t * (3.0 - 2.0 * t))


def uv_of(t):
    """Rounded-rectangle section (high superellipse exponent = coachwork, not barrel)."""
    a = TAU * t
    n = 6.0
    cu, su = math.cos(a), math.sin(a)
    u = math.copysign(abs(cu) ** (2.0 / n), cu)
    v = math.copysign(abs(su) ** (2.0 / n), su)
    return u, v


def v_to_t(v):
    """Inverse of uv_of on the u>0 flank: parameter t for a given height v."""
    s = math.copysign(abs(v) ** (6.0 / 2.0), v)
    return (math.asin(max(-1.0, min(1.0, s))) / TAU) % 1.0


def width_factor(v):
    f = 1.0
    if v > 0.0:
        f -= 0.17 * v ** 2.0
    else:
        f -= 0.26 * (-v) ** 2.2
    f += 0.035 * math.exp(-((v + 0.10) / 0.40) ** 2)
    return f


def surf(x, t):
    u, v = uv_of(t)
    zc = (floor_z(x) + roof_z(x)) * 0.5
    zh = (roof_z(x) - floor_z(x)) * 0.5
    s = end_scale(x)
    y = half_w(x) * u * width_factor(v) * s
    z = zc + zh * v * (0.55 + 0.45 * s)
    return Vector((x, y, z))


def normal_at(x, t, eps=1.5e-3):
    p = surf(x, t)
    dt = surf(x, (t + eps) % 1.0) - p
    dx = surf(min(x + eps * 6, X1), t) - p
    n = dt.cross(dx)
    if n.length < 1e-9:
        return Vector((0, 0, 1))
    n.normalize()
    if n.y * p.y < 0 and abs(p.y) > 0.05:
        n = -n
    return n


WINDOWS = [
    ("door", -0.62, 0.22, 0.20, 0.80),
    ("quarter.rear", -1.14, -0.76, 0.30, 0.76),
    ("quarter.front", 0.58, 0.98, 0.30, 0.76),
]


def is_window(x, t):
    u, v = uv_of(t)
    if abs(u) < 0.84:
        return False
    for _, xa, xb, va, vb in WINDOWS:
        if xa <= x <= xb and va <= v <= vb:
            return True
    return False


# ---------------------------------------------------------------- shell
bm = new_bm()
xs = [X0 + (X1 - X0) * i / NX for i in range(NX + 1)]
rings = [[bm.verts.new(surf(x, j / NT)) for j in range(NT)] for x in xs]
skipped = 0
for i in range(NX):
    xm = (xs[i] + xs[i + 1]) * 0.5
    for j in range(NT):
        k = (j + 1) % NT
        if is_window(xm, (j + 0.5) / NT):
            skipped += 1
            continue
        bm.faces.new((rings[i][j], rings[i][k], rings[i + 1][k], rings[i + 1][j]))
bm.faces.new(rings[0][::-1])
bm.faces.new(rings[-1])

shell = bm_obj(bm, "Body.Shell", C_BODY, smooth=True)
assign_slots(shell, [M_LACQ, M_PANEL])
sol = solidify(shell, thickness=0.05, offset=-1.0)
sol.use_rim = True
sol.material_offset = 1
sol.material_offset_rim = 1
bevel_obj(shell, width=0.008, segments=2, angle=math.radians(25))


# ---------------------------------------------------------------- mouldings
def ribbon(bm, path, w_out=0.026, w_side=0.022, offset=0.008, side=1, closed=False):
    frames = []
    for (x, t) in path:
        p, n = surf(x, t), normal_at(x, t)
        if side < 0:
            p, n = Vector((p.x, -p.y, p.z)), Vector((n.x, -n.y, n.z))
        frames.append((p + n * offset, n))
    rings_ = []
    for i, (p, n) in enumerate(frames):
        if i == 0:
            tan = frames[1][0] - frames[0][0]
        elif i == len(frames) - 1:
            tan = frames[-1][0] - frames[-2][0]
        else:
            tan = frames[i + 1][0] - frames[i - 1][0]
        if tan.length < 1e-9:
            continue
        tan.normalize()
        s = tan.cross(n)
        if s.length < 1e-9:
            continue
        s.normalize()
        rings_.append([tuple(p + s * (du * w_side * 0.5) + n * (dv * w_out * 0.5))
                       for du, dv in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    if closed and rings_:
        rings_.append(rings_[0])
    if len(rings_) > 1:
        loft(bm, rings_, close_loop=True, cap_ends=not closed)


def rounded_rect(xa, xb, va, vb, cx=0.07, cv=0.09, n_edge=9, n_corner=5):
    pts = []

    def push(x, v):
        pts.append((x, v_to_t(max(-0.995, min(0.995, v)))))

    cx = min(cx, abs(xb - xa) * 0.4)
    cv = min(cv, abs(vb - va) * 0.4)
    for i in range(n_edge + 1):
        push(xa + cx + (xb - xa - 2 * cx) * i / n_edge, va)
    for i in range(1, n_corner + 1):
        a = -math.pi / 2 + (math.pi / 2) * i / n_corner
        push(xb - cx + math.cos(a) * cx, va + cv + math.sin(a) * cv)
    for i in range(1, n_edge + 1):
        push(xb, va + cv + (vb - va - 2 * cv) * i / n_edge)
    for i in range(1, n_corner + 1):
        a = (math.pi / 2) * i / n_corner
        push(xb - cx + math.cos(a) * cx, vb - cv + math.sin(a) * cv)
    for i in range(1, n_edge + 1):
        push(xb - cx - (xb - xa - 2 * cx) * i / n_edge, vb)
    for i in range(1, n_corner + 1):
        a = math.pi / 2 + (math.pi / 2) * i / n_corner
        push(xa + cx + math.cos(a) * cx, vb - cv + math.sin(a) * cv)
    for i in range(1, n_edge + 1):
        push(xa, vb - cv - (vb - va - 2 * cv) * i / n_edge)
    for i in range(1, n_corner + 1):
        a = math.pi + (math.pi / 2) * i / n_corner
        push(xa + cx + math.cos(a) * cx, va + cv + math.sin(a) * cv)
    return pts


def h_line(v, xa=None, xb=None, n=48):
    xa = X0 + 0.03 if xa is None else xa
    xb = X1 - 0.03 if xb is None else xb
    return [(xa + (xb - xa) * i / n, v_to_t(v)) for i in range(n + 1)]


bm = new_bm()
for side in (1, -1):
    for _, xa, xb, va, vb in WINDOWS:
        ribbon(bm, rounded_rect(xa - 0.032, xb + 0.032, va - 0.032, vb + 0.032,
                                cx=0.05, cv=0.07),
               w_out=0.028, w_side=0.030, offset=0.003, side=side, closed=True)
    ribbon(bm, rounded_rect(-0.72, 0.32, -0.70, 0.90, cx=0.10, cv=0.12),
           w_out=0.020, w_side=0.026, offset=0.005, side=side, closed=True)
    ribbon(bm, rounded_rect(-0.60, 0.20, -0.58, -0.02, cx=0.08, cv=0.09),
           w_out=0.016, w_side=0.020, offset=0.007, side=side, closed=True)
    ribbon(bm, h_line(0.06), w_out=0.030, w_side=0.036, offset=0.003, side=side)
    ribbon(bm, h_line(0.90), w_out=0.024, w_side=0.028, offset=0.003, side=side)
    ribbon(bm, h_line(-0.82), w_out=0.028, w_side=0.032, offset=0.003, side=side)
mould = bm_obj(bm, "Body.Mouldings", C_BODY, smooth=True)
assign(mould, M_GOLD)

# corner pillars
bm = new_bm()
for side in (1, -1):
    for x in (X0 + 0.14, -0.70, 0.30, X1 - 0.14):
        path = [(x, v_to_t(-0.88 + 1.78 * i / 20)) for i in range(21)]
        ribbon(bm, path, w_out=0.018, w_side=0.050, offset=0.001, side=side)
pillars = bm_obj(bm, "Body.Pillars", C_BODY, smooth=True)
assign(pillars, M_EBONY)

# ---------------------------------------------------------------- suspension straps
bm = new_bm()
CX, CZ, CR = GEO["rear_x"] - 0.34, 0.965, 0.352
for s in (-1, 1):
    top = Vector((CX + math.cos(math.radians(86.0)) * CR, s * 0.86,
                  CZ + math.sin(math.radians(86.0)) * CR))
    body = Vector((X0 + 0.22, s * 0.60, floor_z(X0 + 0.22) + 0.10))
    mid = (top + body) * 0.5 + Vector((-0.02, 0.0, -0.05))
    sweep(bm, [top, mid, body], rect_profile(0.020, 0.105, corner=0.006))
for s in (-1, 1):
    fs = Vector((GEO["front_x"], s * 0.62, GEO["front_axle_z"] + 0.30))
    body = Vector((X1 - 0.30, s * 0.58, floor_z(X1 - 0.30) + 0.06))
    sweep(bm, [fs, (fs + body) * 0.5 + Vector((0.0, 0.0, 0.04)), body],
          rect_profile(0.020, 0.100, corner=0.006))
braces = bm_obj(bm, "Brace.Leather", C_GEAR, smooth=True)
assign(braces, M_LEATHER)

# body bearers resting on the perch and springs
bm = new_bm()
for s in (-1, 1):
    sweep(bm, [(X0 + 0.05, s * 0.52, floor_z(X0 + 0.05) - 0.02),
               (0.0, s * 0.56, FLOOR - 0.03),
               (X1 - 0.05, s * 0.52, floor_z(X1 - 0.05) - 0.02)],
          rect_profile(0.085, 0.075, corner=0.012))
bearers = bm_obj(bm, "Body.Bearers", C_GEAR, smooth=False)
assign(bearers, M_EBONY)
bevel_obj(bearers, width=0.006, segments=2)

bpy.app.driver_namespace["body"] = {
    "surf": surf, "normal": normal_at, "windows": WINDOWS, "v_to_t": v_to_t,
    "floor_z": floor_z, "roof_z": roof_z, "half_w": half_w, "uv": uv_of,
    "x0": X0, "x1": X1, "ribbon": ribbon, "rounded_rect": rounded_rect,
    "end_scale": end_scale,
}
bpy.app.driver_namespace["geo"] = GEO

__result__ = {"shell_faces": len(shell.data.polygons), "windows_cut": skipped,
              "x_range": (X0, X1), "roof": ROOF}
print(__result__)
