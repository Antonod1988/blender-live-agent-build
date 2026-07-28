"""Real intersection test, not eyeballing: BVH overlap between mesh pairs.

Screenshots only show what happens to face the camera. This walks the actual
triangles. A bounding-box prefilter keeps it cheap enough to run every time.
"""
import bpy
from mathutils.bvhtree import BVHTree

dg = bpy.context.evaluated_depsgraph_get()

# groups that must never share space, and the pairs worth testing
GROUPS = ("Sails", "Rig", "Deck", "Super", "Guns", "Details", "Hull")
PAIRS = [("Sails", "Rig"), ("Sails", "Super"), ("Sails", "Deck"),
         ("Sails", "Details"), ("Sails", "Hull"),
         ("Guns", "Deck"), ("Guns", "Super"),
         ("Details", "Deck"), ("Details", "Super"), ("Details", "Hull"),
         ("Details", "Rig"), ("Rig", "Super"), ("Rig", "Deck")]

# a spar goes through a deck, a sail is bent to its yard, a gun sticks out of
# its port: these touch by design and are not worth reporting
EXPECTED = (
    ("Sail", "Yard"), ("Bunt", "Yard"), ("Mast", "Deck"), ("Mast", "Fc.Beam"),
    ("Mast", "Qd.Beam"), ("Mast", "Beam"), ("Bowsprit", "Deck"),
    ("Topmast", "Xtree"), ("Topmast", "Cap"), ("Mast", "Cap"),
    ("Mast", "Top."), ("Topmast", "Top."), ("Lift", "Yard"), ("Sling", "Yard"),
    ("Stays", "Top."), ("Stays", "Mast"), ("Shroud", "Top."),
    ("Flag", "Mast"), ("Flag", "Topmast"), ("Flag", "Topgallant"),
    ("Cathead", "Bulwark"), ("Cathead", "Deck"), ("Cathead", "Fc."),
    ("Anchor", "Cathead"), ("Rudder", "Sternpost"), ("Tiller", "Transom"),
    ("Ladder", "Qd."), ("Ladder", "Fc."),
)


def expected(a, b):
    for x, y in EXPECTED:
        if (x in a and y in b) or (x in b and y in a):
            return True
    return False

members = {}
for g in GROUPS:
    c = bpy.data.collections.get(g)
    obs = []
    for o in (c.all_objects if c else []):
        if o.type in ('MESH', 'CURVE'):
            obs.append(o)
    members[g] = obs

box, tree = {}, {}


def bounds(ob):
    if ob.name in box:
        return box[ob.name]
    m = ob.matrix_world
    pts = [m @ __import__("mathutils").Vector(c) for c in ob.bound_box]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    box[ob.name] = (lo, hi)
    return box[ob.name]


def hit(a, b):
    la, ha = bounds(a)
    lb, hb = bounds(b)
    return all(la[i] <= hb[i] + 0.02 and lb[i] <= ha[i] + 0.02 for i in range(3))


def bvh(ob):
    """World-space tree.

    BVHTree.FromObject builds in the object's LOCAL space, so two objects with
    different transforms get compared in unrelated coordinate systems - which
    silently invents clashes and hides real ones. Feed it world coordinates.
    """
    if ob.name in tree:
        return tree[ob.name]
    tree[ob.name] = None
    ev = ob.evaluated_get(dg)
    try:
        me = ev.to_mesh()
    except Exception:
        return None
    if me and len(me.polygons):
        mw = ob.matrix_world
        verts = [mw @ v.co for v in me.vertices]
        polys = [list(p.vertices) for p in me.polygons]
        try:
            tree[ob.name] = BVHTree.FromPolygons(verts, polys)
        except Exception:
            pass
    ev.to_mesh_clear()
    return tree[ob.name]


seen, clashes = set(), []
for ga, gb in PAIRS:
    for a in members.get(ga, []):
        for b in members.get(gb, []):
            if a is b or a.parent is b or b.parent is a:
                continue
            key = tuple(sorted((a.name, b.name)))
            if key in seen or expected(a.name, b.name) or not hit(a, b):
                continue
            seen.add(key)
            ta, tb = bvh(a), bvh(b)
            if ta is None or tb is None:
                continue
            ov = ta.overlap(tb)
            if ov:
                clashes.append((a.name, b.name, len(ov)))

clashes.sort(key=lambda c: -c[2])
__result__ = {"tested": len(seen), "clashes": len(clashes), "worst": clashes[:14]}
