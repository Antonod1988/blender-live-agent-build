"""Client side of the agent -> Blender bridge (agentkit flow, local variant).

* every payload is prefixed with sys.settrace(None)
* plib.py (and kit.py if present) are injected into Blender and cached by
  source hash, so editing them re-injects on the next call
* the stage source is sent separately as `hud_code` so the viewport strip
  shows the build, not the library
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get("BLENDER_HOST", "127.0.0.1")
PORT = int(os.environ.get("BLENDER_PORT", "9876"))
LIBS = [os.path.join(HERE, "plib.py"), os.path.join(HERE, "ship.py")]

PREAMBLE = "import sys\nsys.settrace(None)\n"


class BlenderError(RuntimeError):
    pass


class Blender:
    def __init__(self, host=HOST, port=PORT, libs=None):
        self.host, self.port = host, port
        self.libs = LIBS if libs is None else libs

    # ------------------------------------------------------------ transport
    def cmd(self, command, params=None, timeout=600):
        req = {"id": uuid.uuid4().hex[:8], "command": command, "params": params or {}}
        s = socket.create_connection((self.host, self.port), timeout=15)
        s.settimeout(timeout)
        try:
            s.sendall(json.dumps(req).encode("utf-8") + b"\n")
            buf = b""
            while b"\n" not in buf:
                chunk = s.recv(65536)
                if not chunk:
                    raise BlenderError("bridge closed the connection")
                buf += chunk
        finally:
            s.close()
        resp = json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))
        if not resp.get("success"):
            raise BlenderError(resp.get("error", "unknown bridge error"))
        return resp["result"]

    def alive(self, timeout=5):
        try:
            self.cmd("scene.get_info", {}, timeout)
            return True
        except Exception:
            return False

    def wait_alive(self, seconds=90):
        deadline = time.time() + seconds
        while time.time() < deadline:
            if self.alive(3):
                return True
            time.sleep(1.0)
        return False

    # ------------------------------------------------------------ execution
    def code(self, src, timeout=280, load_libs=True, hud_code=None,
             title=None, note=None):
        payload = PREAMBLE + (self._lib_source() if load_libs else "") + src
        params = {"code": payload, "timeout_seconds": min(timeout, 300)}
        if hud_code is not None:
            params["hud_code"] = hud_code
        if title is not None:
            params["hud_title"] = title
            params["hud_note"] = note or ""
        res = self.cmd("python.execute", params, timeout + 30)
        return self._unwrap(res)

    def file(self, path, timeout=280, title=None, note=None, hud=True):
        with open(path, encoding="utf-8") as f:
            src = f.read()
        return self.code(src, timeout, hud_code=src if hud else None,
                         title=title, note=note)

    # ------------------------------------------------------------ internals
    def _lib_source(self):
        out = []
        for path in self.libs:
            if not os.path.exists(path):
                continue
            name = os.path.splitext(os.path.basename(path))[0]
            with open(path, encoding="utf-8") as f:
                src = f.read()
            digest = hashlib.sha1(src.encode("utf-8")).hexdigest()
            out.append(
                "import types, sys as _s\n"
                "_h = %r\n"
                "if getattr(_s.modules.get(%r), '__src_hash__', None) != _h:\n"
                "    _m = types.ModuleType(%r)\n"
                "    _m.__src_hash__ = _h\n"
                "    exec(compile(%r, '<%s>', 'exec'), _m.__dict__)\n"
                "    _s.modules[%r] = _m\n"
                "%s = _s.modules[%r]\n" % (digest, name, name, src, name, name, name, name)
            )
        return "".join(out)

    @staticmethod
    def _unwrap(res):
        if res.get("error"):
            raise BlenderError(res["error"])
        if res.get("stdout"):
            print(res["stdout"].rstrip())
        return res.get("result")


if __name__ == "__main__":
    import sys

    bl = Blender()
    if len(sys.argv) > 2 and sys.argv[1] == "exec":
        print(json.dumps(bl.file(sys.argv[2], hud=False), ensure_ascii=False, default=str)[:4000])
    elif len(sys.argv) > 2 and sys.argv[1] == "eval":
        print(json.dumps(bl.code(sys.argv[2]), ensure_ascii=False, default=str)[:4000])
    else:
        print(json.dumps(bl.cmd("scene.get_info"), indent=2))
