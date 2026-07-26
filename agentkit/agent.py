"""Client side of the agent -> Blender bridge.

Improvements over the bare socket client used for the carriage build:

* every payload is prefixed with ``sys.settrace(None)`` - the bridge's cooperative
  timeout tracer costs ~10x on tight Python loops
* ``kit.py`` is auto-loaded inside Blender and cached, so stage scripts can just
  call ``kit.stage(...)`` / ``kit.check(...)``
* long animation renders run in chunks, so the bridge stays responsive and
  progress is visible instead of Blender going dark for 20 minutes
* results are unwrapped: you get the value, or an exception with Blender's traceback
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import time
import uuid

HOST = os.environ.get("BLENDER_HOST", "127.0.0.1")
PORT = int(os.environ.get("BLENDER_PORT", "9876"))
KIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kit.py")

PREAMBLE = "import sys\nsys.settrace(None)\n"


class BlenderError(RuntimeError):
    """Raised when code submitted to Blender fails; carries Blender's traceback."""


class Blender:
    def __init__(self, host: str = HOST, port: int = PORT, kit: str = KIT):
        self.host, self.port, self.kit_path = host, port, kit
        self._kit_loaded = False

    # ---------------------------------------------------------------- transport
    def cmd(self, command: str, params: dict | None = None, timeout: float = 600):
        req = {"id": uuid.uuid4().hex[:8], "command": command, "params": params or {}}
        s = socket.create_connection((self.host, self.port), timeout=15)
        s.settimeout(timeout)
        try:
            s.sendall(json.dumps(req).encode() + b"\n")
            buf = b""
            while b"\n" not in buf:
                chunk = s.recv(65536)
                if not chunk:
                    raise BlenderError("bridge closed the connection")
                buf += chunk
        finally:
            s.close()
        resp = json.loads(buf.split(b"\n", 1)[0])
        if not resp.get("success"):
            raise BlenderError(resp.get("error", "unknown bridge error"))
        return resp["result"]

    def alive(self, timeout: float = 5) -> bool:
        """True if the bridge answers. False while Blender is busy rendering."""
        try:
            self.cmd("scene.get_info", {}, timeout)
            return True
        except Exception:
            return False

    # ---------------------------------------------------------------- execution
    def code(self, src: str, timeout: float = 280, load_kit: bool = True):
        payload = PREAMBLE
        if load_kit:
            payload += self._kit_source()
        payload += src
        res = self.cmd("python.execute", {"code": payload,
                                          "timeout_seconds": min(timeout, 300)}, timeout + 30)
        return self._unwrap(res)

    def file(self, path: str, timeout: float = 280, load_kit: bool = True):
        with open(path, encoding="utf-8") as f:
            return self.code(f.read(), timeout, load_kit)

    def code_async(self, src: str, timeout: float = 3600, load_kit: bool = True):
        payload = PREAMBLE + (self._kit_source() if load_kit else "") + src
        return self.cmd("python.execute_async",
                        {"code": payload, "timeout_seconds": timeout}, 60)["job_id"]

    def job(self, job_id: str):
        return self.cmd("job.status", {"job_id": job_id}, 60)

    def job_wait(self, job_id: str, poll: float = 5.0, on_tick=None):
        while True:
            try:
                st = self.job(job_id)
            except Exception:
                # the bridge is blocked inside a long bpy.ops call - that is expected
                time.sleep(poll)
                continue
            if st["status"] not in ("queued", "running"):
                if st.get("error"):
                    raise BlenderError(st["error"])
                return st["result"]
            if on_tick:
                on_tick(st)
            time.sleep(poll)

    # ---------------------------------------------------------------- rendering
    def render_chunked(self, start: int, end: int, chunk: int = 15, on_chunk=None):
        """Render a frame range in slices so the bridge never goes unresponsive.

        A single ``render(animation=True)`` call blocks Blender's main thread for the
        whole range: no progress, no cancel, no scene queries. Slicing costs a few
        milliseconds per chunk and buys back control.
        """
        done, f = [], start
        while f <= end:
            last = min(f + chunk - 1, end)
            res = self.code(
                "import bpy\n"
                "scn = bpy.context.scene\n"
                f"scn.frame_start, scn.frame_end = {f}, {last}\n"
                "bpy.ops.render.render(animation=True)\n"
                f"__result__ = [{f}, {last}]\n",
                timeout=290, load_kit=False,
            )
            done.append(res)
            if on_chunk:
                on_chunk(last, end)
            f = last + 1
        return {"frames": end - start + 1, "chunks": len(done)}

    # ---------------------------------------------------------------- internals
    def _kit_source(self) -> str:
        with open(self.kit_path, encoding="utf-8") as f:
            src = f.read()
        # kit is injected as a module object so stage scripts can say kit.stage(...).
        # The source hash is stamped on the module: edit kit.py and the next call
        # re-injects it. A stale cached kit once silently deleted a scene's materials.
        digest = hashlib.sha1(src.encode("utf-8")).hexdigest()
        return (
            "import types, sys as _s\n"
            "_h = %r\n"
            "if getattr(_s.modules.get('kit'), '__src_hash__', None) != _h:\n"
            "    _m = types.ModuleType('kit')\n"
            "    _m.__src_hash__ = _h\n"
            "    exec(compile(%r, '<kit>', 'exec'), _m.__dict__)\n"
            "    _s.modules['kit'] = _m\n"
            "kit = _s.modules['kit']\n" % (digest, src)
        )

    @staticmethod
    def _unwrap(res: dict):
        if res.get("error"):
            raise BlenderError(res["error"])
        out = res.get("result")
        if res.get("stdout"):
            print(res["stdout"].rstrip())
        return out

    def reload_kit(self):
        """Force the next call to re-inject kit.py (after editing it)."""
        self.code("import sys\nsys.modules.pop('kit', None)\n__result__ = 'kit dropped'\n",
                  load_kit=False)


if __name__ == "__main__":
    import sys

    bl = Blender()
    if len(sys.argv) > 1 and sys.argv[1] == "exec":
        print(json.dumps(bl.file(sys.argv[2]), ensure_ascii=False, indent=2)[:4000])
    else:
        print(json.dumps(bl.cmd("scene.get_info"), indent=2))
