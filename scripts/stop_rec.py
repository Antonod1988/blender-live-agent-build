import os
import sys

import bpy

sys.settrace(None)
ns = bpy.app.driver_namespace
st = ns.get("mcp_rec")
if st:
    st["on"] = False
fn = ns.get("mcp_rec_fn")
if fn and bpy.app.timers.is_registered(fn):
    bpy.app.timers.unregister(fn)

d = st["dir"] if st else None
n = len(os.listdir(d)) if d and os.path.isdir(d) else 0
__result__ = {"stopped": True, "frames": n, "errors": (st or {}).get("errors", [])}
print(__result__)
