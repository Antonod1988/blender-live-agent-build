import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())

C_DET = get_coll("Details", get_coll("Carriage"))
B = bpy.app.driver_namespace["body"]
surf, normal_at, v_to_t = B["surf"], B["normal"], B["v_to_t"]

M_GOLD = bpy.data.materials["Gold.Ornament"]
M_ENAMEL = bpy.data.materials["Lacquer.Black"]
M_FIELD = bpy.data.materials["Velvet.Crimson"]
M_CRYSTAL = bpy.data.materials["Crystal.Arcane"]

for n in ("Door.Crest", "Door.Sigil"):
    ob = bpy.data.objects.get(n)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)

# pole gem: its own, much dimmer material so it stops reading as a lens flare
gemmat = mat("Crystal.PoleGem", base=(0.22, 0.48, 0.95), emission=(0.30, 0.60, 1.0),
             emission_strength=2.2, rough=0.10, transmission=0.7, ior=1.7, alpha=0.7)
gem = bpy.data.objects.get("Harness.PoleGem")
if gem:
    assign(gem, gemmat)
gl = bpy.data.objects.get("PoleGemLight")
if gl:
    gl.data.energy = 4.0


def shield_outline(w, h, n=34):
    """Classic heraldic shield: flat top, curved flanks, pointed base."""
    pts = []
    for i in range(n):
        t = i / n
        a = TAU * t
        c, s = math.cos(a), math.sin(a)
        if s >= 0.0:                       # upper half: near-rectangular
            u = c * w * (1.0 - 0.10 * s ** 3)
            v = h * 0.42 * (s ** 0.45)
        else:                              # lower half: tapering to a point
            k = -s
            u = c * w * (1.0 - k ** 1.35)
            v = -h * 0.58 * (k ** 0.75)
        pts.append((u, v))
    return pts


def place(side, x, v, off):
    t = v_to_t(v)
    p, n = surf(x, t), normal_at(x, t)
    if side < 0:
        p, n = Vector((p.x, -p.y, p.z)), Vector((n.x, -n.y, n.z))
    tan = Vector((1.0, 0.0, 0.0))
    up = n.cross(tan).normalized()
    if up.z < 0:
        up = -up
    return p + n * off, n, tan, up


bm_g, bm_f = new_bm(), new_bm()
for side in (1, -1):
    base, n, tan, up = place(side, -0.19, -0.28, 0.004)
    outline = shield_outline(0.135, 0.34)
    # gold rim: two offset outlines lofted into a raised bezel
    rim_rows = []
    for k, (sc, off) in enumerate(((1.00, 0.004), (1.00, 0.030), (0.86, 0.030), (0.86, 0.004))):
        rim_rows.append([tuple(base + n * (off - 0.004) + tan * (u * sc) + up * (v * sc))
                         for u, v in outline])
    rim_rows.append(rim_rows[0])
    loft(bm_g, rim_rows, close_loop=True, cap_ends=False)

    # enamel field inside the bezel
    field_rows = []
    for sc, off in ((0.86, 0.026), (0.86, 0.014)):
        field_rows.append([tuple(base + n * off + tan * (u * sc) + up * (v * sc))
                           for u, v in outline])
    loft(bm_f, field_rows, close_loop=True, cap_ends=True)

    # charge: a bend with three mullets
    for i, (du, dv) in enumerate(((-0.055, 0.072), (0.0, 0.0), (0.055, -0.072))):
        c = base + n * 0.031 + tan * du + up * dv
        for k in range(5):
            a = TAU * k / 5 + math.pi / 2
            tip = c + tan * (math.cos(a) * 0.030) + up * (math.sin(a) * 0.030)
            mid1 = c + tan * (math.cos(a + math.pi / 5) * 0.013) + up * (math.sin(a + math.pi / 5) * 0.013)
            mid2 = c + tan * (math.cos(a - math.pi / 5) * 0.013) + up * (math.sin(a - math.pi / 5) * 0.013)
            try:
                v0 = bm_g.verts.new(tuple(tip))
                v1 = bm_g.verts.new(tuple(mid1))
                v2 = bm_g.verts.new(tuple(c))
                v3 = bm_g.verts.new(tuple(mid2))
                bm_g.faces.new((v0, v1, v2, v3))
            except ValueError:
                pass

    # coronet above the shield
    top = base + up * 0.20
    ring = []
    for k in range(18):
        a = TAU * k / 18
        ring.append(tuple(top + tan * (math.cos(a) * 0.075) + n * (math.sin(a) * 0.022)))
    ring2 = [tuple(Vector(p) + up * 0.042) for p in ring]
    loft(bm_g, [ring, ring2], close_loop=True, cap_ends=False)
    for du in (-0.058, -0.020, 0.020, 0.058):
        tipc = top + tan * du + up * 0.070
        cone(bm_g, tuple(tipc), 0.014, 0.002, 0.040, axis="Z", segments=6)
        sphere(bm_g, tuple(tipc + up * 0.028), 0.011, segments=8, rings=5)

crest = bm_obj(bm_g, "Door.Crest", C_DET, smooth=True)
assign(crest, M_GOLD)
field = bm_obj(bm_f, "Door.CrestField", C_DET, smooth=False)
assign(field, M_FIELD)

__result__ = {"rebuilt": ["Door.Crest", "Door.CrestField"], "pole_gem_mat": gemmat.name}
print(__result__)
