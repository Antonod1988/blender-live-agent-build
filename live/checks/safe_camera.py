"""Frame the whole ship, keep the eye outside it, keep the orbit moving.

focus() only ever names a point to look at. Left alone it pushes in until the
subject fills the frame and the ship stops being readable, and with a low
elevation the eye ends up inside the hull. This wraps focus so every move
keeps the whole 34-metre hull in shot and the eye out of it.
"""
import bpy
import math
import types
from mathutils import Vector, Quaternion

BOX = ((-17.5, 17.5), (-5.6, 5.6), (-3.2, 7.6))   # ship space
MIN_DIST = 25.0        # close enough to read a fitting, wide enough to see the ship
PULL = 0.40            # how far each detail shot drifts back to the ship centre
ORBIT = 4.5            # degrees per second


def _root_z():
    root = bpy.data.objects.get("ShipRoot")
    return root.location.z if root else 0.0


def _eye(target, dist, elev, az):
    q = (Quaternion((0.0, 0.0, 1.0), az)
         @ Quaternion((1.0, 0.0, 0.0), math.pi / 2.0 - elev))
    return Vector(target) + q @ Vector((0.0, 0.0, dist))


def _inside(p):
    z = _root_z()
    local = (p.x, p.y, p.z - z)
    return all(lo <= local[i] <= hi for i, (lo, hi) in enumerate(BOX))


def focus_safe(self, target=None, dist=None, elev=None, az=None, secs=6.0):
    tgt = target
    if tgt is None:
        tgt = self.target
    elif hasattr(tgt, "matrix_world"):
        tgt = tgt.matrix_world.translation
    elif isinstance(tgt, str):
        ob = bpy.data.objects.get(tgt)
        tgt = ob.matrix_world.translation if ob else self.target
    tgt = Vector(tgt).lerp(Vector((0.0, 0.0, 1.4 + _root_z())), PULL)

    d = max(MIN_DIST, self.dist if dist is None else float(dist))
    e = self.elev if elev is None else math.radians(elev)
    e = max(math.radians(6.0), e)
    a = self.az if az is None else math.radians(az)
    for _ in range(60):
        if not _inside(_eye(tgt, d, e, a)):
            break
        d += 1.2
    return self._focus_raw(target=tuple(tgt), dist=d,
                           elev=math.degrees(e), az=math.degrees(a), secs=secs)


def _pull_back_later(self, delay, shot):
    """After a close-up has been held, drift back to the whole ship."""
    def cb():
        if getattr(self, "_shot", None) != shot:
            return None                      # a newer shot took over
        self._focus_raw(target=(0.0, 0.0, 2.2 + _root_z()), dist=36.0,
                        elev=17.0, az=math.degrees(self.az) + 26.0, secs=6.0)
        return None
    bpy.app.timers.register(cb, first_interval=max(1.0, delay))


def detail(self, target, dist=13.0, elev=14.0, az=None, secs=5.0, hold=4.5):
    """Close on a small fitting: no drift back to centre, eye still outside."""
    tgt = target
    if hasattr(tgt, "matrix_world"):
        tgt = tgt.matrix_world.translation
    elif isinstance(tgt, str):
        ob = bpy.data.objects.get(tgt)
        tgt = ob.matrix_world.translation if ob else self.target
    tgt = Vector(tgt)
    d = max(7.0, float(dist))
    e = max(math.radians(4.0), math.radians(elev))
    a = self.az if az is None else math.radians(az)
    for _ in range(70):
        if not _inside(_eye(tgt, d, e, a)):
            break
        d += 1.0
    ts = getattr(self, "timescale", 1.0)
    self._shot = getattr(self, "_shot", 0) + 1
    if hold < 60.0:          # a huge hold means "stay put"; do not queue a
        _pull_back_later(self, (secs + hold) * ts, self._shot)   # stray move
    return self._focus_raw(target=tuple(tgt), dist=d,
                           elev=math.degrees(e), az=math.degrees(a), secs=secs)


def focus_raw(self, target=None, dist=None, elev=None, az=None, secs=6.0):
    """Every move goes through here, so one knob scales them all.

    When the build is replayed fast the stages still ask for eight-second
    moves; the camera then never arrives anywhere and the ship appears to
    build itself off screen. timescale shrinks the moves to match the pace.
    """
    return self._focus_orig(target=target, dist=dist, elev=elev, az=az,
                            secs=max(0.30, secs * getattr(self, "timescale", 1.0)))


if not hasattr(director, "_focus_orig"):
    director._focus_orig = director._focus_raw if hasattr(director, "_focus_raw") \
        else director.focus
director.timescale = getattr(director, "timescale", 1.0)
director._focus_raw = types.MethodType(focus_raw, director)
director.focus = types.MethodType(focus_safe, director)
director.detail = types.MethodType(detail, director)
director.orbit(ORBIT)

__result__ = {"min_dist": MIN_DIST, "orbit_deg_s": ORBIT}
