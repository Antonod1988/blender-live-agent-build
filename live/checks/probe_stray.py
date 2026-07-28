import bpy

dg = bpy.context.evaluated_depsgraph_get()
out = []
for ob in bpy.data.objects:
    if ob.type not in ('MESH', 'CURVE') or ob.name in ("Ocean", "SeaFar"):
        continue
    ev = ob.evaluated_get(dg)
    try:
        pts = [ev.matrix_world @ v.co for v in ev.to_mesh().vertices]
    except Exception:
        continue
    if not pts:
        ev.to_mesh_clear()
        continue
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    ev.to_mesh_clear()
    span = max(hi[i] - lo[i] for i in range(3))
    far = max(abs(lo[0]), abs(hi[0]), abs(lo[1]), abs(hi[1]))
    if span > 34.0 or far > 18.0:
        out.append((ob.name, round(span, 1),
                    [round(v, 1) for v in lo], [round(v, 1) for v in hi]))
out.sort(key=lambda t: -t[1])
__result__ = out[:16]
