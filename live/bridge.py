"""Live bridge: agent -> Blender, plus viewport HUD and camera director.

Run inside Blender:
    blender --factory-startup empty.blend --python bridge.py

Protocol (newline-delimited JSON on 127.0.0.1:9876), compatible with the
agentkit client:
    {"id":..,"command":"python.execute","params":{"code":..,"timeout_seconds":..}}
    -> {"success":true,"result":{"result":..,"stdout":..,"error":null}}

Submitted code runs on Blender's MAIN thread (drained from a bpy.app.timers
callback), so the viewport updates live while the scene is being built.

Two extras beyond the plain bridge:
  * hud      - a thin code strip along the bottom of the viewport that types
               out the code currently being executed
  * director - owns the viewport view itself: a permanent slow orbit that can
               be eased onto whatever detail is being added right now
"""

import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Quaternion, Vector

import io
import json
import math
import queue
import socket
import sys
import threading
import traceback
import uuid
from contextlib import redirect_stdout

HOST, PORT = "127.0.0.1", 9876

# ----------------------------------------------------------------- execution
GLOBALS = {"__name__": "__bridge__", "bpy": bpy}
_inbox = queue.Queue()
_jobs = {}


def _run_job(job):
    job["status"] = "running"
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            GLOBALS.pop("__result__", None)
            exec(compile(job["code"], "<agent>", "exec"), GLOBALS)
        job["result"] = GLOBALS.pop("__result__", None)
        job["status"] = "done"
    except Exception:
        job["error"] = traceback.format_exc()
        job["status"] = "error"
    job["stdout"] = buf.getvalue()
    if job.get("_event"):
        job["_event"].set()


def _drain():
    for _ in range(4):
        try:
            job = _inbox.get_nowait()
        except queue.Empty:
            break
        _run_job(job)
    return 0.02


# ----------------------------------------------------------------------- HUD
class Hud:
    """A small strip of code along the bottom edge of the viewport."""

    MAX = 6

    def __init__(self):
        self.lines = []
        self.pending = []
        self.title = ""
        self.note = ""
        self.handle = None
        self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')

    # ---- content
    def stage(self, title, note=""):
        self.title, self.note = title, note
        self.redraw()

    def feed(self, code, limit=400):
        keep = []
        for ln in str(code).splitlines():
            s = ln.rstrip()
            t = s.strip()
            if not t or t.startswith("#"):
                continue
            keep.append(s[:150])
        self.pending.extend(keep[-limit:])

    def say(self, text):
        self.pending.append(str(text))

    def tick(self):
        if self.pending:
            n = max(1, len(self.pending) // 10)
            for _ in range(n):
                if not self.pending:
                    break
                self.lines.append(self.pending.pop(0))
            del self.lines[:-self.MAX]
            self.redraw()
        return 0.045

    def redraw(self):
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

    # ---- drawing
    def _bar(self, x0, y0, x1, y1, color):
        verts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        batch = batch_for_shader(self.shader, 'TRIS', {"pos": verts},
                                 indices=[(0, 1, 2), (0, 2, 3)])
        self.shader.uniform_float("color", color)
        batch.draw(self.shader)

    def draw(self):
        region = bpy.context.region
        if region is None:
            return
        w, h = region.width, region.height
        pad, lh = 18, 15
        rows = max(1, len(self.lines))
        bar_h = pad + rows * lh + (22 if self.title else 6)

        gpu.state.blend_set('ALPHA')
        self._bar(0, 0, w, bar_h, (0.02, 0.025, 0.035, 0.62))
        self._bar(0, bar_h, w, bar_h + 1, (0.85, 0.66, 0.36, 0.28))
        gpu.state.blend_set('NONE')

        f = 0
        y = pad * 0.45
        blf.size(f, 13)
        for i, ln in enumerate(reversed(self.lines)):
            a = 0.85 - i * 0.115
            blf.color(f, 0.72, 0.80, 0.86, max(0.16, a))
            blf.position(f, 22, y + (len(self.lines) - 1 - i) * lh, 0)
            blf.draw(f, ln)
        if self.title:
            ty = y + rows * lh + 5
            blf.size(f, 14)
            blf.color(f, 0.92, 0.74, 0.42, 0.95)
            blf.position(f, 22, ty, 0)
            blf.draw(f, self.title)
            if self.note:
                blf.size(f, 12)
                blf.color(f, 0.55, 0.60, 0.66, 0.75)
                nw = blf.dimensions(f, self.note)[0]
                blf.position(f, max(24, w - 24 - nw), ty + 1, 0)
                blf.draw(f, self.note)

    def install(self):
        if self.handle is None:
            self.handle = bpy.types.SpaceView3D.draw_handler_add(
                self.draw, (), 'WINDOW', 'POST_PIXEL')


# ------------------------------------------------------------------ director
def _smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


class Director:
    """Owns the viewport view: permanent slow orbit, eased focus moves."""

    DT = 1.0 / 30.0

    def __init__(self):
        self.az = math.radians(-55.0)
        self.elev = math.radians(14.0)
        self.dist = 40.0
        self.target = Vector((0.0, 0.0, 0.0))
        self.spin = math.radians(1.6)      # degrees per second
        self.tw = None
        self.enabled = True

    def orbit(self, deg_per_sec):
        self.spin = math.radians(deg_per_sec)

    def focus(self, target=None, dist=None, elev=None, az=None, secs=6.0):
        """Ease the view onto a detail. Non-blocking: returns immediately."""
        a = {"target": self.target.copy(), "dist": self.dist,
             "elev": self.elev, "az": self.az}
        if target is None:
            tgt = self.target.copy()
        elif hasattr(target, "matrix_world"):
            tgt = target.matrix_world.translation.copy()
        elif isinstance(target, str):
            ob = bpy.data.objects.get(target)
            tgt = ob.matrix_world.translation.copy() if ob else self.target.copy()
        else:
            tgt = Vector(target)
        b = {"target": tgt,
             "dist": self.dist if dist is None else float(dist),
             "elev": self.elev if elev is None else math.radians(elev),
             "az": None if az is None else math.radians(az)}
        if b["az"] is not None:
            d = (b["az"] - a["az"] + math.pi) % (2 * math.pi) - math.pi
            b["az"] = a["az"] + d
        self.tw = {"a": a, "b": b, "t": 0.0, "secs": max(0.2, float(secs))}
        return "focus"

    def tick(self):
        if not self.enabled:
            return self.DT
        if self.tw:
            tw = self.tw
            tw["t"] += self.DT
            f = _smooth(tw["t"] / tw["secs"])
            a, b = tw["a"], tw["b"]
            self.target = a["target"].lerp(b["target"], f)
            self.dist = a["dist"] + (b["dist"] - a["dist"]) * f
            self.elev = a["elev"] + (b["elev"] - a["elev"]) * f
            if b["az"] is None:
                self.az += self.spin * self.DT
            else:
                self.az = (a["az"] + (b["az"] - a["az"]) * f) + self.spin * tw["t"]
            if tw["t"] >= tw["secs"]:
                self.tw = None
        else:
            self.az += self.spin * self.DT

        q = (Quaternion((0.0, 0.0, 1.0), self.az)
             @ Quaternion((1.0, 0.0, 0.0), math.pi / 2.0 - self.elev))
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                if area.type != 'VIEW_3D':
                    continue
                r3d = area.spaces.active.region_3d
                if r3d is None:
                    continue
                r3d.view_perspective = 'PERSP'
                r3d.view_rotation = q
                r3d.view_location = self.target
                r3d.view_distance = self.dist
        return self.DT


hud = Hud()
director = Director()
GLOBALS["hud"] = hud
GLOBALS["director"] = director


# -------------------------------------------------------------------- server
def _dispatch(req):
    cmd = req.get("command")
    p = req.get("params") or {}
    try:
        if cmd == "scene.get_info":
            return {"success": True,
                    "result": {"blender": bpy.app.version_string,
                               "queued": _inbox.qsize()}}
        if cmd in ("python.execute", "python.execute_async"):
            job = {"id": uuid.uuid4().hex[:8], "code": p.get("code", ""),
                   "status": "queued", "result": None, "error": None,
                   "stdout": "", "hud": p.get("hud_code")}
            if job["hud"]:
                hud.feed(job["hud"])
            if p.get("hud_title"):
                hud.stage(p["hud_title"], p.get("hud_note", ""))
            _jobs[job["id"]] = job
            if cmd == "python.execute_async":
                _inbox.put(job)
                return {"success": True, "result": {"job_id": job["id"]}}
            ev = threading.Event()
            job["_event"] = ev
            _inbox.put(job)
            if not ev.wait(float(p.get("timeout_seconds", 300)) + 10):
                return {"success": False, "error": "main thread did not answer in time"}
            return {"success": True,
                    "result": {"result": job["result"], "stdout": job["stdout"],
                               "error": job["error"]}}
        if cmd == "job.status":
            j = _jobs.get(p.get("job_id"))
            if not j:
                return {"success": False, "error": "unknown job"}
            return {"success": True,
                    "result": {"status": j["status"], "result": j["result"],
                               "error": j["error"], "stdout": j["stdout"]}}
        return {"success": False, "error": "unknown command %r" % cmd}
    except Exception:
        return {"success": False, "error": traceback.format_exc()}


def _handle(conn):
    conn.settimeout(3600)
    f = conn.makefile("rwb")
    try:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                req = json.loads(raw.decode("utf-8"))
                resp = _dispatch(req)
            except Exception as exc:
                resp = {"success": False, "error": "bad request: %s" % exc}
            f.write(json.dumps(resp, ensure_ascii=False, default=str).encode("utf-8") + b"\n")
            f.flush()
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _serve():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(8)
    print("[bridge] listening on %s:%d" % (HOST, PORT))
    while True:
        try:
            conn, _ = srv.accept()
        except OSError:
            break
        threading.Thread(target=_handle, args=(conn,), daemon=True).start()


# ---------------------------------------------------------------- UI cleanup
def _maximize():
    """One fullscreen 3D viewport, no headers, no panels."""
    try:
        bpy.context.preferences.view.show_statusbar = False
        bpy.context.preferences.view.show_navigate_ui = False
    except Exception:
        pass
    try:
        if not bpy.context.window.screen.show_fullscreen:
            bpy.ops.wm.window_fullscreen_toggle()
    except Exception as exc:
        print("[bridge] fullscreen toggle skipped:", exc)
    for win in bpy.context.window_manager.windows:
        areas = list(win.screen.areas)
        if len(areas) == 1 and areas[0].type == 'VIEW_3D':
            continue
        for area in areas:
            if area.type == 'VIEW_3D':
                try:
                    with bpy.context.temp_override(window=win, area=area):
                        bpy.ops.screen.screen_full_area(use_hide_panels=True)
                except Exception as exc:
                    print("[bridge] maximize failed:", exc)
                break
    return None


def _configure():
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            sp = area.spaces.active
            sp.shading.type = 'RENDERED'
            sp.overlay.show_overlays = False
            sp.show_gizmo = False
            sp.show_region_ui = False
            sp.show_region_toolbar = False
            sp.show_region_header = False
            sp.lens = 40.0
            sp.clip_start = 0.05
            sp.clip_end = 4000.0
    hud.install()
    hud.stage("bridge ready", "waiting for the agent")
    if not bpy.app.timers.is_registered(director.tick):
        bpy.app.timers.register(director.tick, persistent=True)
    if not bpy.app.timers.is_registered(hud.tick):
        bpy.app.timers.register(hud.tick, persistent=True)
    print("[bridge] viewport configured")
    return None


bpy.app.timers.register(_drain, persistent=True)
bpy.app.timers.register(_maximize, first_interval=0.6)
bpy.app.timers.register(_configure, first_interval=1.4)
threading.Thread(target=_serve, daemon=True).start()
