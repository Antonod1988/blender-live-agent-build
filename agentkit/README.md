# agentkit — the flow, hardened

The carriage was built with a bare 40-line socket client. That worked, but it cost real
time in ways that are easy to name afterwards:

| what went wrong | cost | what fixes it here |
|---|---|---|
| Body proportions judged from one hero render | two full rebuilds of the body | `kit.sheet()` — four-view contact sheet |
| Turntable built with a 1.46 m radius by mistake | one render round-trip to notice | `kit.check().dims()` — fails loudly, instantly |
| A human scaled the scene in the viewport mid-build | ~30 min of confusion | `kit.guard(fix=True)` — detects and reverts |
| Re-running a stage duplicated geometry | manual delete code in every script | `with kit.stage(...)` — idempotent by construction |
| The bridge's timeout tracer | ~10× slowdown on tight loops | `agent.py` prefixes `sys.settrace(None)` |
| `render(animation=True)` blocked Blender for 20 min | no progress, no cancel | `bl.render_chunked()` |
| Grass/cobbles as one giant mesh | ~60 s per stage | `kit.scatter()` — vertex instancing |

Everything below is verified against a live Blender by [`selftest.py`](selftest.py).

## Use

```python
from agent import Blender

bl = Blender()                      # 127.0.0.1:9876, override via BLENDER_HOST/PORT
bl.code("kit.workspace(r'D:/out')") # where previews, sheets and versions go
bl.file("stages/s4_wheels.py")      # kit is injected automatically
```

Inside Blender, `kit` is already imported:

```python
with kit.stage("wheels", version=True) as st:
    ...build...

kit.check("wheels") \
   .dims("Wheel.RearL.Tyre", (1.56, 1.56, 0.12)) \
   .grounded("Wheel.RearL.Tyre", z=-0.11) \
   .unit_scale() \
   .done()                          # raises with every failure listed at once

kit.sheet("wheels_check")           # 4-view clay sheet, ~1 s
```

## What each piece does

**`kit.stage(name, version=False)`** — on enter, deletes every object a previous run of the
same stage created (they carry an `_agent_stage` property); on exit, tags what appeared and
reports object/face counts and elapsed time. Optionally snapshots a `.blend` per stage, so a
bad step is one file away from being undone.

**`kit.check(label)`** — chainable assertions: `dims`, `inside`, `grounded`, `faces`,
`unit_scale`. Collects *all* failures then raises once, so one round-trip tells you
everything that is wrong rather than the first thing.

**`kit.guard(expect=None, fix=False)`** — snapshots every object's location and scale. Given a
previous snapshot it reports drift. With `fix=True` it recognises a uniform
scale-about-a-pivot applied to many objects, solves the pivot from an object authored at the
origin (`P = loc / (1 - s)`) and reverts it. Verified to restore coordinates exactly.

**`kit.preview(tag)`** — OpenGL grab through the scene camera, ~0.3 s. Use this for "did the
thing appear in roughly the right place", and save the beauty render for when it matters.

**`kit.sheet(tag, objects=None)`** — renders front / side / top orthographic plus a
three-quarter perspective and tiles them into one PNG with numpy. Proportion errors are
obvious here and nearly invisible in a hero shot.

**`kit.scatter(name, points, prototype)`** — parents a prototype to a point cloud with
`instance_type='VERTS'`. One mesh, N instances, no geometry duplication.

**`bl.render_chunked(start, end, chunk=15)`** — renders a frame range in slices. Blender stays
answerable between chunks, so you get progress and can stop.

## Self-test

```bash
python agentkit/selftest.py
```

Ten checks against whatever scene is open: bridge reachability, kit injection, preview,
contact sheet, assertions passing, assertions failing loudly, stage idempotency (run twice →
still 3 objects), guard detection, stage teardown, summary.

## Deliberate non-features

`purge_orphans()` clears unused meshes and curves but **not** materials — an unused material
is usually one you are about to assign, and deleting it silently is worse than leaking it.
The first draft of this file purged materials and quietly removed five from the carriage
scene. That is the kind of helpfulness you do not want in a build pipeline.
