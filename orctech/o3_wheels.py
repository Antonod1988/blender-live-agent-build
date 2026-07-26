"""Stage 3 - mismatched wheels. Big lugged rears, scavenged fronts, one spare."""
OLIB = r"D:\pythonProject4\blender-live-agent-build\orctech\olib.py"
exec(open(OLIB, encoding="utf-8").read(), globals())

C = get_coll("Buggy")
CW = get_coll("Wheels", C)

REAR_R, REAR_W = 0.92, 0.52
FRONT_R, FRONT_W = 0.54, 0.30
REAR_X, REAR_Y = -1.05, 1.02
FRONT_X, FRONT_Y = 1.62, 0.86
GROUND = 0.0


def tyre(bm, R, W, lugs, seed):
    """A fat tyre built from a ring of chunky, uneven lugs."""
    r = rng(seed)
    inner = R - 0.20
    rings = []
    for i in range(26):
        a = TAU * i / 26
        wob = 1.0 + 0.012 * math.sin(a * 3.0 + seed)
        rings.append((math.cos(a) * R * wob, math.sin(a) * R * wob))
    sections = []
    for z, k in ((-W / 2, 0.86), (-W / 2 * 0.72, 1.0), (W / 2 * 0.72, 1.0), (W / 2, 0.86)):
        sections.append([(x * k, y * k, z) for x, y in rings])
    loft(bm, sections, closed=True, caps=False)
    # inner wall back to the rim
    for z in (-W / 2, W / 2):
        sgn = 1 if z > 0 else -1
        loft(bm, [[(x * 0.86, y * 0.86, z) for x, y in rings],
                  [(math.cos(TAU * i / 26) * inner, math.sin(TAU * i / 26) * inner,
                    z - sgn * 0.04) for i in range(26)]], closed=True, caps=False)
    # tread lugs, deliberately uneven
    for i in range(lugs):
        a = TAU * i / lugs + r.uniform(-0.05, 0.05)
        depth = r.uniform(0.06, 0.115)
        wide = r.uniform(0.55, 0.85) * W
        skew = r.uniform(-0.18, 0.18)
        cen = (math.cos(a) * (R + depth * 0.35), math.sin(a) * (R + depth * 0.35), skew * W * 0.3)
        vs = box(bm, cen, (0.16, 0.16, wide), rot=(0.0, 0.0, a))
        for v in vs:
            v.co.x *= 1.0
        batter(vs, 0.012, 9.0, seed + i)
    return inner


def rim(bm, R, W, bolts, seed):
    inner = R - 0.20
    prof = [(inner + 0.02, -W / 2 + 0.05), (inner + 0.02, W / 2 - 0.05),
            (inner * 0.42, W / 2 - 0.10), (inner * 0.42, -W / 2 + 0.10)]
    rings = []
    for i in range(20):
        a = TAU * i / 20
        rings.append([(math.cos(a) * p[0], math.sin(a) * p[0], p[1]) for p in prof])
    # dish plate
    loft(bm, [[(math.cos(TAU * i / 20) * inner, math.sin(TAU * i / 20) * inner, 0.02)
               for i in range(20)],
              [(math.cos(TAU * i / 20) * 0.10, math.sin(TAU * i / 20) * 0.10, -0.03)
               for i in range(20)]], closed=True, caps=True)
    del rings
    # hub barrel and bolts
    cyl(bm, (0, 0, 0.0), 0.14, W * 0.75, seg=12)
    cyl(bm, (0, 0, W * 0.42), 0.075, 0.10, seg=8)
    r = rng(seed)
    for i in range(bolts):
        a = TAU * i / bolts + r.uniform(-0.03, 0.03)
        p = (math.cos(a) * 0.23, math.sin(a) * 0.23, 0.055)
        cyl(bm, p, 0.032, 0.05, seg=6)
    # a few holes patched with welded scrap
    for i in range(3):
        a = r.uniform(0, TAU)
        vs = box(bm, (math.cos(a) * (inner * 0.62), math.sin(a) * (inner * 0.62), 0.03),
                 (0.20, 0.16, 0.035), rot=(0, 0, r.uniform(0, TAU)))
        batter(vs, 0.012, 8.0, seed + i)


def build_wheel(name, R, W, lugs, bolts, seed, loc, spin):
    bm = new_bm()
    tyre(bm, R, W, lugs, seed)
    ob_t = bm_obj(bm, name + ".Tyre", CW, mat="Orc.Rubber", split=42)
    bm = new_bm()
    rim(bm, R, W, bolts, seed)
    ob_r = bm_obj(bm, name + ".Rim", CW, mat="Orc.Plate", bevel=0.006, split=40)
    root = bpy.data.objects.new(name, None)
    root.empty_display_type = "CIRCLE"
    root.empty_display_size = R
    CW.objects.link(root)
    for o in (ob_t, ob_r):
        o.parent = root
    root.location = loc
    root.rotation_euler = (math.radians(90), spin, 0.0)
    return root


made = []
with kit.stage("wheels") as st:
    r = rng(4041)
    made.append(build_wheel("Wheel.RearL", REAR_R, REAR_W, 22, 8, 11,
                            (REAR_X, REAR_Y, GROUND + REAR_R - 0.035), r.uniform(0, TAU)))
    made.append(build_wheel("Wheel.RearR", REAR_R * 0.97, REAR_W, 20, 8, 23,
                            (REAR_X, -REAR_Y, GROUND + REAR_R * 0.97 - 0.03), r.uniform(0, TAU)))
    made.append(build_wheel("Wheel.FrontL", FRONT_R, FRONT_W, 16, 6, 37,
                            (FRONT_X, FRONT_Y, GROUND + FRONT_R - 0.02), r.uniform(0, TAU)))
    made.append(build_wheel("Wheel.FrontR", FRONT_R * 1.06, FRONT_W * 0.85, 14, 6, 51,
                            (FRONT_X, -FRONT_Y, GROUND + FRONT_R * 1.06 - 0.02),
                            r.uniform(0, TAU)))
    # spare, bolted flat to the back
    spare = build_wheel("Wheel.Spare", REAR_R * 0.82, REAR_W * 0.8, 18, 8, 67,
                        (-2.18, 0.0, 1.28), 0.4)
    spare.rotation_euler = (0.0, math.radians(96.0), 0.0)
    made.append(spare)

    # Lugs stick out past the nominal radius, so seat each wheel on its measured
    # silhouette rather than on the number it was designed from.
    bpy.context.view_layer.update()
    for root in made:
        if root.name == "Wheel.Spare":
            continue
        low = min((child.matrix_world @ v.co).z
                  for child in root.children for v in child.data.vertices)
        sink = 0.045 if "Rear" in root.name else 0.03
        root.location.z += (GROUND - sink) - low
    bpy.context.view_layer.update()

kit.check("wheels") \
   .dims("Wheel.RearL.Tyre", (REAR_R * 2.2, REAR_R * 2.2, None), tol=0.20) \
   .grounded("Wheel.RearL.Tyre", z=GROUND - 0.045, tol=0.02) \
   .grounded("Wheel.FrontR.Tyre", z=GROUND - 0.030, tol=0.02) \
   .unit_scale([o.name for o in made]) \
   .done()

__result__ = {"stage": st.report(), "sheet": kit.sheet("03_wheels")}
