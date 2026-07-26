import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())

C_BODY = get_coll("Body", get_coll("Carriage"))
GEO = bpy.app.driver_namespace["geo"]

M_LACQ = bpy.data.materials["Lacquer.Burgundy"]
M_PANEL = bpy.data.materials["Panel.Inlay"]
M_GOLD = bpy.data.materials["Gold.Ornament"]
M_GOLD_D = bpy.data.materials["Gold.Dark"]
M_VELVET = bpy.data.materials["Velvet.Crimson"]
M_EBONY = bpy.data.materials["Wood.Ebony"]

# ---------------------------------------------------------------- body surface
X0, X1 = GEO["body_x0"], GEO["body_x1"]
XC = (X0 + X1) * 0.5
XH = (X1 - X0) * 0.5
FLOOR, ROOF = GEO["floor_z"], GEO["roof_z"]
HW = GEO["body_hw"]
NT = 64          # points around a section
NX = 44          # stations along the body


def xn_of(x):
    return (x - XC) / XH


def floor_z(x):
    return FLOOR + 0.30 * abs(xn_of(x)) ** 2.6


def roof_z(x):
    return ROOF - 0.075 * xn_of(x) ** 2


def half_w(x):
    return HW * (1.0 - 0.17 * abs(xn_of(x)) ** 2.3)


def uv_of(t):
    """Superellipse outline -> (u, v) in [-1, 1]: a softly rounded rectangle."""
    a = TAU * t
    n = 3.1
    cu, su = math.cos(a), math.sin(a)
    u = math.copysign(abs(cu) ** (2.0 / n), cu)
    v = math.copysign(abs(su) ** (2.0 / n), su)
    return u, v


def width_factor(v):
    """Tumblehome: the coach swells at the waist and tucks in top and bottom."""
    f = 1.0
    if v > 0.0:
        f -= 0.20 * v ** 1.7          # roof narrower
    else:
        f -= 0.34 * (-v) ** 1.9       # underbody tucked in
    f += 0.05 * math.exp(-((v + 0.15) / 0.45) ** 2)   # waist swell
    return f


def surf(x, t):
    u, v = uv_of(t)
    zc = (floor_z(x) + roof_z(x)) * 0.5
    zh = (roof_z(x) - floor_z(x)) * 0.5
    y = half_w(x) * u * width_factor(v)
    z = zc + zh * v
    return Vector((x, y, z))


def normal_at(x, t, eps=1e-3):
    p = surf(x, t)
    dt = surf(x, (t + eps) % 1.0) - p
    dx = surf(min(x + eps * 4, X1), t) - p
    n = dt.cross(dx)
    if n.length < 1e-9:
        return Vector((0, 0, 1))
    n.normalize()
    if n.dot(Vector((0.0, p.y, 0.0))) < 0 and abs(p.y) > 1e-4:
        n = -n
    return n


# window openings, expressed in (x, v) space on the flanks
WINDOWS = [
    ("door", -1.02, -0.18, 0.24, 0.82),
    ("quarter", 0.12, 0.48, 0.32, 0.80),
]


def is_window(x, t):
    u, v = uv_of(t)
    if abs(u) < 0.80:
        return False
    for _, xa, xb, va, vb in WINDOWS:
        if xa <= x <= xb and va <= v <= vb:
            return True
    return False


# ---------------------------------------------------------------- shell mesh
bm = new_bm()
rings = []
xs = [X0 + (X1 - X0) * i / NX for i in range(NX + 1)]
for x in xs:
    rings.append([bm.verts.new(surf(x, j / NT)) for j in range(NT)])

skipped = 0
for i in range(NX):
    xm = (xs[i] + xs[i + 1]) * 0.5
    for j in range(NT):
        k = (j + 1) % NT
        tm = (j + 0.5) / NT
        if is_window(xm, tm):
            skipped += 1
            continue
        bm.faces.new((rings[i][j], rings[i][k], rings[i + 1][k], rings[i + 1][j]))

# flat end walls
bm.faces.new(rings[0][::-1])
bm.faces.new(rings[-1])

shell = bm_obj(bm, "Body.Shell", C_BODY, smooth=False)
assign_slots(shell, [M_LACQ, M_PANEL])
sol = solidify(shell, thickness=0.055, offset=-1.0)
sol.use_rim = True
sol.material_offset = 1
sol.material_offset_rim = 1
bevel_obj(shell, width=0.010, segments=2, angle=math.radians(28))

# ---------------------------------------------------------------- mouldings
def surf_ribbon(bm, path_uv, w_out=0.026, w_side=0.020, offset=0.008, side=1,
                closed=False):
    """Sweep a rectangular moulding along a path given in (x, t) surface space."""
    frames = []
    for (x, t) in path_uv:
        p = surf(x, t)
        n = normal_at(x, t)
        if side < 0:
            p = Vector((p.x, -p.y, p.z))
            n = Vector((n.x, -n.y, n.z))
        frames.append((p + n * offset, n))
    rings = []
    for i, (p, n) in enumerate(frames):
        if i == 0:
            tan = frames[1][0] - frames[0][0]
        elif i == len(frames) - 1:
            tan = frames[-1][0] - frames[-2][0]
        else:
            tan = frames[i + 1][0] - frames[i - 1][0]
        tan.normalize()
        s = tan.cross(n).normalized()
        ring = []
        for du, dv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            ring.append(tuple(p + s * (du * w_side * 0.5) + n * (dv * w_out * 0.5)))
        rings.append(ring)
    if closed:
        rings.append(rings[0])
    loft(bm, rings, close_loop=True, cap_ends=not closed)


def rect_path(xa, xb, va, vb, corner=0.06, steps=9):
    """A rounded rectangle in (x, v) space, returned as (x, t) samples."""
    def t_of_v(v, front):
        # find the t on the flank matching v (u > 0 half)
        a = math.asin(max(-1.0, min(1.0, math.copysign(abs(v) ** (3.1 / 2.0), v))))
        t = a / TAU
        if not front:
            t = 0.5 - t if False else t
        return t % 1.0

    pts = []
    span_x = xb - xa
    span_v = vb - va
    cx = min(corner, abs(span_x) * 0.35)
    cv = min(corner * 1.4, abs(span_v) * 0.35)

    def edge(x_from, x_to, v_from, v_to, n):
        out = []
        for i in range(n + 1):
            f = i / n
            out.append((x_from + (x_to - x_from) * f, t_of_v(v_from + (v_to - v_from) * f, True)))
        return out

    def corner_arc(cxx, cvv, a0, a1, n=4):
        out = []
        for i in range(n + 1):
            a = a0 + (a1 - a0) * i / n
            out.append((cxx + math.cos(a) * cx, t_of_v(cvv + math.sin(a) * cv, True)))
        return out

    pts += edge(xa + cx, xb - cx, va, va, steps)
    pts += corner_arc(xb - cx, va + cv, -math.pi / 2, 0.0)
    pts += edge(xb, xb, va + cv, vb - cv, max(3, steps // 2))
    pts += corner_arc(xb - cx, vb - cv, 0.0, math.pi / 2)
    pts += edge(xb - cx, xa + cx, vb, vb, steps)
    pts += corner_arc(xa + cx, vb - cv, math.pi / 2, math.pi)
    pts += edge(xa, xa, vb - cv, va + cv, max(3, steps // 2))
    pts += corner_arc(xa + cx, va + cv, math.pi, 1.5 * math.pi)
    return pts


bm = new_bm()
for side in (1, -1):
    # window surrounds
    for _, xa, xb, va, vb in WINDOWS:
        surf_ribbon(bm, rect_path(xa - 0.035, xb + 0.035, va - 0.035, vb + 0.035, corner=0.05),
                    w_out=0.030, w_side=0.030, offset=0.004, side=side, closed=True)
    # door outline
    surf_ribbon(bm, rect_path(-1.20, 0.02, -0.66, 0.90, corner=0.10),
                w_out=0.022, w_side=0.026, offset=0.006, side=side, closed=True)
    # lower panel frame inside the door
    surf_ribbon(bm, rect_path(-1.06, -0.14, -0.54, 0.08, corner=0.08),
                w_out=0.018, w_side=0.020, offset=0.008, side=side, closed=True)
    # waist rail running the full length
    waist = [(X0 + (X1 - X0) * i / 40.0, None) for i in range(41)]
    path = []
    for i in range(41):
        x = X0 + 0.02 + (X1 - X0 - 0.04) * i / 40.0
        v = 0.12
        a = math.asin(math.copysign(abs(v) ** (3.1 / 2.0), v))
        path.append((x, (a / TAU) % 1.0))
    surf_ribbon(bm, path, w_out=0.030, w_side=0.034, offset=0.004, side=side)
    # roof edge and skirt rails
    for v, wo, ws in ((0.90, 0.026, 0.030), (-0.80, 0.030, 0.034)):
        path = []
        for i in range(41):
            x = X0 + 0.02 + (X1 - X0 - 0.04) * i / 40.0
            a = math.asin(math.copysign(abs(abs(v)) ** (3.1 / 2.0), v))
            path.append((x, (a / TAU) % 1.0))
        surf_ribbon(bm, path, w_out=wo, w_side=ws, offset=0.004, side=side)

mould = bm_obj(bm, "Body.Mouldings", C_BODY, smooth=True)
assign(mould, M_GOLD)

# ---------------------------------------------------------------- corner pillars
bm = new_bm()
for side in (1, -1):
    for x in (X0 + 0.10, -1.24, 0.06, X1 - 0.10):
        path = []
        for i in range(19):
            v = -0.86 + 1.74 * i / 18
            a = math.asin(math.copysign(abs(abs(v)) ** (3.1 / 2.0), v))
            path.append((x, (a / TAU) % 1.0))
        surf_ribbon(bm, path, w_out=0.020, w_side=0.052, offset=0.002, side=side)
pillars = bm_obj(bm, "Body.Pillars", C_BODY, smooth=True)
assign(pillars, M_EBONY)

bpy.app.driver_namespace["body"] = {
    "surf": surf, "normal": normal_at, "windows": WINDOWS,
    "floor_z": floor_z, "roof_z": roof_z, "half_w": half_w,
    "x0": X0, "x1": X1, "uv": uv_of,
}

__result__ = {"shell_faces": len(shell.data.polygons), "window_faces_removed": skipped,
              "moulding_faces": len(mould.data.polygons)}
print(__result__)
