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
M_BLACK = bpy.data.materials["Lacquer.Black"]

# calmer lacquer: less mirror-coat so the burgundy actually reads
for name, rough, coat in (("Lacquer.Burgundy", 0.24, 0.35), ("Lacquer.Black", 0.22, 0.30)):
    b = bpy.data.materials[name].node_tree.nodes.get("Principled BSDF")
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat

for n in ("Body.Shell", "Body.Mouldings", "Body.Pillars", "Body.Roof"):
    ob = bpy.data.objects.get(n)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)

X0, X1 = -1.30, 1.28
FLOOR, ROOFLINE = 1.06, 2.28
HW = 0.715
GEO.update({"body_x0": X0, "body_x1": X1, "body_hw": HW,
            "floor_z": FLOOR, "roof_z": ROOFLINE})
XC, XH = (X0 + X1) * 0.5, (X1 - X0) * 0.5
NT, NX = 80, 60
SE = 7.0        # superellipse exponent: flat panels, tight corner radii


def xn_of(x):
    return (x - XC) / XH


def floor_z(x):
    return FLOOR + 0.115 * abs(xn_of(x)) ** 3.0


def roof_z(x):
    return ROOFLINE - 0.030 * xn_of(x) ** 2


def half_w(x):
    return HW * (1.0 - 0.055 * abs(xn_of(x)) ** 3.0)


def end_scale(x):
    a = abs(xn_of(x))
    if a < 0.80:
        return 1.0
    t = (a - 0.80) / 0.20
    return 1.0 - 0.16 * (t * t * (3.0 - 2.0 * t))


def uv_of(t):
    a = TAU * t
    cu, su = math.cos(a), math.sin(a)
    return (math.copysign(abs(cu) ** (2.0 / SE), cu),
            math.copysign(abs(su) ** (2.0 / SE), su))


def v_to_t(v):
    s = math.copysign(abs(v) ** (SE / 2.0), v)
    return (math.asin(max(-1.0, min(1.0, s))) / TAU) % 1.0


def width_factor(v):
    if v > 0.0:
        return 1.0 - 0.11 * v ** 2.2
    return 1.0 - 0.22 * (-v) ** 2.4


def surf(x, t):
    u, v = uv_of(t)
    zc = (floor_z(x) + roof_z(x)) * 0.5
    zh = (roof_z(x) - floor_z(x)) * 0.5
    y = half_w(x) * u * width_factor(v) * end_scale(x)
    return Vector((x, y, zc + zh * v))


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
    ("door", -0.60, 0.24, 0.18, 0.78),
    ("quarter.rear", -1.14, -0.78, 0.28, 0.74),
    ("quarter.front", 0.60, 0.98, 0.28, 0.74),
]


def is_window(x, t):
    u, v = uv_of(t)
    if abs(u) < 0.86:
        return False
    for _, xa, xb, va, vb in WINDOWS:
        if xa <= x <= xb and va <= v <= vb:
            return True
    return False


bm = new_bm()
xs = [X0 + (X1 - X0) * i / NX for i in range(NX + 1)]
rings = [[bm.verts.new(surf(x, j / NT)) for j in range(NT)] for x in xs]
cut = 0
for i in range(NX):
    xm = (xs[i] + xs[i + 1]) * 0.5
    for j in range(NT):
        k = (j + 1) % NT
        if is_window(xm, (j + 0.5) / NT):
            cut += 1
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
es = shell.modifiers.new("EdgeSplit", "EDGE_SPLIT")
es.split_angle = math.radians(31.0)
bevel_obj(shell, width=0.007, segments=2, angle=math.radians(24))

# ---------------------------------------------------------------- roof slab
bm = new_bm()
RX0, RX1 = X0 - 0.055, X1 + 0.055
NRX, NRT = 40, 40
roof_rings = []
for i in range(NRX + 1):
    x = RX0 + (RX1 - RX0) * i / NRX
    xr = max(-1.0, min(1.0, (x - XC) / (XH + 0.055)))
    w = (HW * 1.035) * (1.0 - 0.055 * abs(xr) ** 3.0) * (1.0 - 0.10 * max(0.0, abs(xr) - 0.82) / 0.18)
    zb = roof_z(min(max(x, X0), X1)) - 0.015
    ring = []
    for j in range(NRT):
        t = j / NRT
        a = TAU * t
        cu, su = math.cos(a), math.sin(a)
        u = math.copysign(abs(cu) ** (2.0 / 5.0), cu)
        v = math.copysign(abs(su) ** (2.0 / 5.0), su)
        y = w * u * (1.0 - 0.10 * max(v, 0.0) ** 2)
        z = zb + 0.055 + 0.062 * v - 0.025 * (u * u) * max(v, 0.0)
        ring.append((x, y, z))
    roof_rings.append(ring)
loft(bm, roof_rings, close_loop=True, cap_ends=True)
roof = bm_obj(bm, "Body.Roof", C_BODY, smooth=True)
assign(roof, M_BLACK)
re = roof.modifiers.new("EdgeSplit", "EDGE_SPLIT")
re.split_angle = math.radians(33.0)
bevel_obj(roof, width=0.008, segments=2, angle=math.radians(26))


# ---------------------------------------------------------------- mouldings
def ribbon(bm, path, w_out=0.026, w_side=0.022, offset=0.008, side=1, closed=False):
    frames = []
    for (x, t) in path:
        p, n = surf(x, t), normal_at(x, t)
        if side < 0:
            p, n = Vector((p.x, -p.y, p.z)), Vector((n.x, -n.y, n.z))
        frames.append((p + n * offset, n))
    out = []
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
        out.append([tuple(p + s * (du * w_side * 0.5) + n * (dv * w_out * 0.5))
                    for du, dv in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    if closed and out:
        out.append(out[0])
    if len(out) > 1:
        loft(bm, out, close_loop=True, cap_ends=not closed)


def rounded_rect(xa, xb, va, vb, cx=0.07, cv=0.09, n_edge=9, n_corner=5):
    pts = []

    def push(x, v):
        pts.append((x, v_to_t(max(-0.99, min(0.99, v)))))

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


def h_line(v, xa=None, xb=None, n=52):
    xa = X0 + 0.04 if xa is None else xa
    xb = X1 - 0.04 if xb is None else xb
    return [(xa + (xb - xa) * i / n, v_to_t(v)) for i in range(n + 1)]


bm = new_bm()
for side in (1, -1):
    for _, xa, xb, va, vb in WINDOWS:
        ribbon(bm, rounded_rect(xa - 0.030, xb + 0.030, va - 0.030, vb + 0.030,
                                cx=0.05, cv=0.06),
               w_out=0.026, w_side=0.030, offset=0.003, side=side, closed=True)
    ribbon(bm, rounded_rect(-0.70, 0.34, -0.72, 0.88, cx=0.09, cv=0.11),
           w_out=0.020, w_side=0.026, offset=0.005, side=side, closed=True)
    ribbon(bm, rounded_rect(-0.58, 0.22, -0.60, -0.04, cx=0.07, cv=0.08),
           w_out=0.015, w_side=0.019, offset=0.007, side=side, closed=True)
    ribbon(bm, h_line(0.04), w_out=0.028, w_side=0.034, offset=0.003, side=side)
    ribbon(bm, h_line(0.86), w_out=0.022, w_side=0.026, offset=0.003, side=side)
    ribbon(bm, h_line(-0.84), w_out=0.026, w_side=0.030, offset=0.003, side=side)
mould = bm_obj(bm, "Body.Mouldings", C_BODY, smooth=True)
assign(mould, M_GOLD)

bm = new_bm()
for side in (1, -1):
    for x in (X0 + 0.13, -0.68, 0.32, X1 - 0.13):
        ribbon(bm, [(x, v_to_t(-0.90 + 1.80 * i / 22)) for i in range(23)],
               w_out=0.016, w_side=0.048, offset=0.001, side=side)
pillars = bm_obj(bm, "Body.Pillars", C_BODY, smooth=True)
assign(pillars, M_EBONY)

d = bpy.app.driver_namespace.get("body", {})
d.update({"surf": surf, "normal": normal_at, "windows": WINDOWS, "v_to_t": v_to_t,
          "floor_z": floor_z, "roof_z": roof_z, "half_w": half_w, "uv": uv_of,
          "x0": X0, "x1": X1, "ribbon": ribbon, "rounded_rect": rounded_rect,
          "end_scale": end_scale, "width_factor": width_factor, "xn": xn_of})
bpy.app.driver_namespace["body"] = d
bpy.app.driver_namespace["geo"] = GEO

__result__ = {"shell_faces": len(shell.data.polygons), "windows_cut": cut}
print(__result__)
