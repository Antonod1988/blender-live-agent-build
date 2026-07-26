"""Undo a uniform scale-about-a-pivot that was applied to the scene objects."""
import sys

import bpy
from mathutils import Vector

sys.settrace(None)

ref = bpy.data.objects["Body.Shell"]          # was authored at the world origin
s = ref.scale.x
report = {"factor": round(s, 5)}

if abs(s - 1.0) < 1e-4:
    report["status"] = "nothing to undo"
else:
    P = Vector(ref.location) / (1.0 - s)      # pivot of the stray scale
    report["pivot"] = tuple(round(v, 4) for v in P)
    fixed = []
    for o in bpy.data.objects:
        if abs(o.scale.x - s) < 1e-3 and abs(o.scale.y - s) < 1e-3:
            o.location = P + (Vector(o.location) - P) / s
            o.scale = (o.scale.x / s, o.scale.y / s, o.scale.z / s)
            fixed.append(o.name)
    report["fixed_count"] = len(fixed)
    report["sample"] = fixed[:8]
    report["status"] = "restored"

bpy.context.view_layer.update()
w = bpy.data.objects.get("Wheel.FrontL")
report["wheel_front_l"] = tuple(round(v, 3) for v in w.location) if w else None
c = bpy.data.objects["HeroCam"]
report["cam"] = (tuple(round(v, 3) for v in c.location), tuple(round(v, 3) for v in c.scale))
__result__ = report
print(report)
