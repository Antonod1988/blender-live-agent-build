"""In-Blender half of the toolkit. Injected by agent.py, available as ``kit``.

Four things the carriage build lacked and paid for:

* ``stage()``      - idempotent stages, so re-running a script never doubles geometry
* ``check()``      - dimension asserts, so a turntable with a 1.46 m radius fails loudly
* ``guard()``      - catches a human scaling the scene in the viewport mid-build
* ``sheet()``      - a 4-view contact sheet in ~1 s instead of a 4 s beauty render
"""

import math
import os
import time

import bpy
import numpy as np
from mathutils import Vector

STAGE_KEY = "_agent_stage"
_state = {"out": None, "versions": None}


# --------------------------------------------------------------------- paths
def workspace(path=None):
    """Set (or read) the directory previews, sheets and versions are written to."""
    if path:
        _state["out"] = path
        _state["versions"] = os.path.join(path, "versions")
        os.makedirs(path, exist_ok=True)
        os.makedirs(_state["versions"], exist_ok=True)
    if not _state["out"]:
        base = bpy.app.tempdir or os.getcwd()
        workspace(os.path.join(base, "agent_out"))
    return _state["out"]


# --------------------------------------------------------------------- stages
class stage:
    """Context manager giving a build step an identity.

    On enter it removes everything a previous run of the same stage created, so a
    stage script is safe to re-run any number of times. On exit it tags whatever
    appeared, records a poly count, and optionally snapshots the .blend.
    """

    def __init__(self, name, version=False, quiet=False):
        self.name = name
        self.version = version
        self.quiet = quiet
        self.before = None
        self.created = []
        self.t0 = 0.0

    def __enter__(self):
        stale = [o for o in bpy.data.objects if o.get(STAGE_KEY) == self.name]
        for o in stale:
            bpy.data.objects.remove(o, do_unlink=True)
        purge_orphans()
        self.before = set(bpy.data.objects.keys())
        self.t0 = time.monotonic()
        if not self.quiet:
            print("[stage %s] cleared %d stale objects" % (self.name, len(stale)))
        return self

    def __exit__(self, exc_type, exc, tb):
        # Tag even on failure. A stage that raised half-way still created objects, and
        # if they go untagged the next run cannot clean them up - it just builds a
        # second set beside them under .001 names.
        self.created = [o for o in bpy.data.objects if o.name not in self.before]
        if exc_type is not None:
            for o in self.created:
                o[STAGE_KEY] = self.name
            print("[stage %s] FAILED after creating %d objects (tagged for cleanup)"
                  % (self.name, len(self.created)))
            return False
        tris = 0
        for o in self.created:
            o[STAGE_KEY] = self.name
            if o.type == "MESH":
                tris += len(o.data.polygons)
        if self.version:
            save_version(self.name)
        if not self.quiet:
            print("[stage %s] +%d objects, %d faces, %.2fs"
                  % (self.name, len(self.created), tris, time.monotonic() - self.t0))
        return False

    def report(self):
        return {"stage": self.name, "objects": [o.name for o in self.created]}


def purge_orphans():
    """Drop unused mesh/curve data left behind by a stage teardown.

    Materials are deliberately NOT purged: an unused material is usually one you are
    about to assign, not garbage, and losing it silently is worse than leaking it.
    """
    for coll in (bpy.data.meshes, bpy.data.curves):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


def save_version(tag):
    path = os.path.join(workspace() and _state["versions"], "%s.blend" % tag)
    bpy.ops.wm.save_as_mainfile(filepath=path, copy=True, compress=True)
    return path


# --------------------------------------------------------------------- checks
class CheckFailed(AssertionError):
    pass


class check:
    """Collect dimension/placement assertions and fail with all of them at once.

    Cheap, and it catches the class of bug that otherwise costs a render round-trip:
    a part built at the wrong scale, mirrored to the wrong side, or floating.
    """

    def __init__(self, label="checks", strict=True):
        self.label, self.strict, self.fails, self.passes = label, strict, [], 0

    def _fail(self, msg):
        self.fails.append(msg)

    def _ok(self):
        self.passes += 1

    def obj(self, name):
        o = bpy.data.objects.get(name)
        if o is None:
            self._fail("missing object %r" % name)
        return o

    def dims(self, name, expect, tol=0.15):
        """World-space bounding box size, within a relative tolerance."""
        o = self.obj(name)
        if not o:
            return self
        d = o.dimensions
        for axis, got, want in zip("xyz", d, expect):
            if want is None:
                continue
            if want == 0:
                ok = abs(got) <= tol
            else:
                ok = abs(got - want) <= abs(want) * tol
            if not ok:
                self._fail("%s.%s = %.3f, expected %.3f (+-%d%%)"
                           % (name, axis, got, want, tol * 100))
            else:
                self._ok()
        return self

    def inside(self, name, lo, hi):
        """Every vertex must sit inside an axis-aligned box - catches runaway geometry."""
        o = self.obj(name)
        if not o or o.type != "MESH":
            return self
        mw = o.matrix_world
        pts = [mw @ v.co for v in o.data.vertices]
        if not pts:
            self._fail("%s has no geometry" % name)
            return self
        for i, axis in enumerate("xyz"):
            mn = min(p[i] for p in pts)
            mx = max(p[i] for p in pts)
            if mn < lo[i] - 1e-4 or mx > hi[i] + 1e-4:
                self._fail("%s extends %.2f..%.2f on %s, allowed %.2f..%.2f"
                           % (name, mn, mx, axis, lo[i], hi[i]))
            else:
                self._ok()
        return self

    def grounded(self, name, z, tol=0.05):
        o = self.obj(name)
        if not o or o.type != "MESH":
            return self
        mw = o.matrix_world
        mn = min((mw @ v.co).z for v in o.data.vertices)
        if abs(mn - z) > tol:
            self._fail("%s sits at z=%.3f, expected %.3f (+-%.3f)" % (name, mn, z, tol))
        else:
            self._ok()
        return self

    def faces(self, name, lo=1, hi=None):
        o = self.obj(name)
        if not o or o.type != "MESH":
            return self
        n = len(o.data.polygons)
        if n < lo or (hi is not None and n > hi):
            self._fail("%s has %d faces, expected %s..%s" % (name, n, lo, hi))
        else:
            self._ok()
        return self

    def unit_scale(self, names=None):
        names = names or [o.name for o in bpy.data.objects]
        for n in names:
            o = bpy.data.objects.get(n)
            if o and any(abs(s - 1.0) > 1e-3 for s in o.scale):
                self._fail("%s carries object scale %s" % (n, tuple(round(s, 3) for s in o.scale)))
            else:
                self._ok()
        return self

    def done(self):
        result = {"label": self.label, "passed": self.passes, "failed": len(self.fails),
                  "problems": self.fails}
        if self.fails:
            print("[check %s] %d FAILED" % (self.label, len(self.fails)))
            for f in self.fails:
                print("   x", f)
            if self.strict:
                raise CheckFailed("%s: %s" % (self.label, "; ".join(self.fails)))
        else:
            print("[check %s] %d assertions passed" % (self.label, self.passes))
        return result


# --------------------------------------------------------------------- guard
def guard(expect=None, fix=False):
    """Detect a human transforming the scene in the viewport behind the agent's back.

    ``expect`` is a snapshot from a previous ``guard()`` call. Returns a report and,
    with ``fix=True``, reverts a uniform scale-about-a-pivot (the exact accident that
    hit the carriage build: 80 objects at scale 4.79482).
    """
    snap = {o.name: (tuple(round(v, 5) for v in o.location),
                     tuple(round(v, 5) for v in o.scale)) for o in bpy.data.objects}
    drift = []
    if expect:
        for name, (loc, scl) in snap.items():
            was = expect.get(name)
            if not was:
                continue
            if any(abs(a - b) > 1e-3 for a, b in zip(scl, was[1])):
                drift.append({"object": name, "scale_was": was[1], "scale_now": scl})
    scaled = {n: s for n, (l, s) in snap.items() if any(abs(v - 1.0) > 1e-3 for v in s)}
    report = {"objects": len(snap), "scaled": len(scaled), "drift": drift[:20],
              "snapshot": snap}

    if fix and scaled:
        factors = {}
        for s in scaled.values():
            factors[round(s[0], 5)] = factors.get(round(s[0], 5), 0) + 1
        f = max(factors, key=factors.get)
        if factors[f] > 3 and abs(f - 1.0) > 1e-3:
            ref = next(o for o in bpy.data.objects
                       if abs(o.scale.x - f) < 1e-3 and o.type == "MESH")
            pivot = Vector(ref.location) / (1.0 - f)
            n = 0
            for o in bpy.data.objects:
                if abs(o.scale.x - f) < 1e-3:
                    o.location = pivot + (Vector(o.location) - pivot) / f
                    o.scale = tuple(v / f for v in o.scale)
                    n += 1
            report["reverted"] = {"factor": f, "pivot": tuple(round(v, 4) for v in pivot),
                                  "objects": n}
            print("[guard] reverted a stray scale of %.5f on %d objects" % (f, n))
    return report


# --------------------------------------------------------------------- previews
def _view3d():
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            return area, next(r for r in area.regions if r.type == "WINDOW")
    return None, None


def preview(tag, res=520, samples=None):
    """Fast OpenGL grab through the scene camera. ~0.3 s instead of a 4 s render."""
    scn = bpy.context.scene
    keep = (scn.render.filepath, scn.render.resolution_x, scn.render.resolution_y,
            scn.render.image_settings.file_format, scn.render.resolution_percentage)
    path = os.path.join(workspace(), "%s.png" % tag)
    scn.render.image_settings.file_format = "PNG"
    scn.render.resolution_x = res
    scn.render.resolution_y = int(res * 9 / 16)
    scn.render.resolution_percentage = 100
    scn.render.filepath = path
    area, region = _view3d()
    try:
        if area:
            with bpy.context.temp_override(area=area, region=region):
                bpy.ops.render.opengl(write_still=True, view_context=False)
        else:
            bpy.ops.render.opengl(write_still=True, view_context=False)
    finally:
        (scn.render.filepath, scn.render.resolution_x, scn.render.resolution_y,
         scn.render.image_settings.file_format, scn.render.resolution_percentage) = keep
    return path


def bounds(objects=None):
    objects = objects or [o for o in bpy.context.scene.objects if o.type == "MESH"]
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objects:
        for corner in o.bound_box:
            p = o.matrix_world @ Vector(corner)
            lo = Vector((min(lo.x, p.x), min(lo.y, p.y), min(lo.z, p.z)))
            hi = Vector((max(hi.x, p.x), max(hi.y, p.y), max(hi.z, p.z)))
    return lo, hi


def sheet(tag, objects=None, res=440, margin=1.15):
    """Front / side / top / three-quarter contact sheet in one PNG.

    Proportion mistakes are obvious in orthographic views and nearly invisible in a
    single hero render - the carriage body spent two rebuilds looking like a barrel
    because nobody was looking at it from the side.
    """
    scn = bpy.context.scene
    lo, hi = bounds(objects)
    ctr = (lo + hi) * 0.5
    size = max((hi - lo).x, (hi - lo).y, (hi - lo).z) * margin
    dist = size * 2.5

    cam_data = bpy.data.cameras.new("_sheet_cam")
    cam = bpy.data.objects.new("_sheet_cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    old_cam = scn.camera
    scn.camera = cam

    views = [
        ("front", (ctr.x, ctr.y - dist, ctr.z), (math.pi / 2, 0, 0), True),
        ("side", (ctr.x + dist, ctr.y, ctr.z), (math.pi / 2, 0, math.pi / 2), True),
        ("top", (ctr.x, ctr.y, ctr.z + dist), (0, 0, 0), True),
        ("persp", (ctr.x + dist * 0.62, ctr.y - dist * 0.62, ctr.z + dist * 0.42), None, False),
    ]
    tiles = []
    for name, loc, rot, ortho in views:
        cam_data.type = "ORTHO" if ortho else "PERSP"
        cam_data.ortho_scale = size
        cam_data.lens = 50
        cam.location = loc
        if rot:
            cam.rotation_euler = rot
        else:
            d = (ctr - Vector(loc)).normalized()
            cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
        tiles.append(preview("_sheet_%s" % name, res=res))

    scn.camera = old_cam
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(cam_data)

    out = os.path.join(workspace(), "%s.png" % tag)
    _tile(tiles, out)
    for t in tiles:
        try:
            os.remove(t)
        except OSError:
            pass
    return out


def _tile(paths, out_path):
    """Compose 4 images into a 2x2 grid using numpy and Blender's image API."""
    imgs = []
    for p in paths:
        im = bpy.data.images.load(p)
        w, h = im.size
        buf = np.empty(w * h * 4, dtype=np.float32)
        im.pixels.foreach_get(buf)
        imgs.append(buf.reshape(h, w, 4))
        bpy.data.images.remove(im)
    h, w = imgs[0].shape[:2]
    canvas = np.zeros((h * 2, w * 2, 4), dtype=np.float32)
    canvas[..., 3] = 1.0
    # image rows run bottom-up, so row 0 of the canvas is the *lower* tile row
    canvas[h:, :w] = imgs[0]
    canvas[h:, w:] = imgs[1]
    canvas[:h, :w] = imgs[2]
    canvas[:h, w:] = imgs[3]
    out = bpy.data.images.new("_sheet", width=w * 2, height=h * 2, alpha=True)
    out.pixels.foreach_set(canvas.ravel())
    out.filepath_raw = out_path
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(out)
    return out_path


# --------------------------------------------------------------------- scatter
def scatter(name, points, prototype, collection=None, rotations=None, scales=None):
    """Instance a prototype object over points instead of duplicating its geometry.

    The carriage build spent ~60 s per stage building grass and cobbles as one giant
    mesh. Vertex instancing puts the same work on the GPU and keeps the .blend small.
    """
    me = bpy.data.meshes.new(name + "Points")
    me.from_pydata([tuple(p) for p in points], [], [])
    me.update()
    holder = bpy.data.objects.new(name, me)
    coll = collection or bpy.context.scene.collection
    coll.objects.link(holder)
    holder.instance_type = "VERTS"
    holder.use_instance_vertices_rotation = bool(rotations)
    prototype.parent = holder
    prototype.matrix_parent_inverse = holder.matrix_world.inverted()
    return holder


# --------------------------------------------------------------------- info
def summary():
    scn = bpy.context.scene
    tris = sum(len(o.data.polygons) for o in scn.objects if o.type == "MESH")
    stages = {}
    for o in bpy.data.objects:
        s = o.get(STAGE_KEY)
        if s:
            stages[s] = stages.get(s, 0) + 1
    return {"objects": len(scn.objects), "faces": tris, "materials": len(bpy.data.materials),
            "stages": stages, "workspace": workspace(),
            "engine": scn.render.engine, "camera": getattr(scn.camera, "name", None)}
