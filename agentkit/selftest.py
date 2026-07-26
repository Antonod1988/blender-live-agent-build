"""Exercise every toolkit feature against whatever scene is currently open."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent import Blender, BlenderError  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_out")
bl = Blender()

print("1. bridge reachable:", bl.alive())

print("2. kit loads + workspace")
print(bl.code("kit.workspace(%r)\n__result__ = kit.summary()\n" % OUT))

print("3. fast preview")
print(bl.code("__result__ = kit.preview('probe')\n"))

print("4. contact sheet (4 ortho/persp views tiled)")
print(bl.code(
    "import bpy\n"
    "objs = [o for o in bpy.data.objects if o.type=='MESH' and "
    "        any(o.name.startswith(p) for p in ('Body','Wheel','Box','Axle','Harness','Roof'))]\n"
    "__result__ = kit.sheet('contact', objects=objs)\n", timeout=120))

print("5. assertions on the carriage")
try:
    print(bl.code(
        "c = kit.check('carriage')\n"
        "c.dims('Body.Shell', (2.58, 1.44, 1.30), tol=0.20)\n"
        "c.unit_scale()\n"
        "c.faces('Body.Shell', lo=1000)\n"
        "__result__ = c.done()\n"))
except BlenderError as e:
    print("   assertions reported failures (expected if the scene differs):", str(e)[:200])

print("6. deliberate failure is loud")
try:
    bl.code("c = kit.check('should_fail')\n"
            "c.dims('Body.Shell', (99.0, 99.0, 99.0))\n"
            "__result__ = c.done()\n")
    print("   !! no exception raised - bad")
except BlenderError as e:
    print("   raised as expected:", str(e).splitlines()[-1][:120])

print("7. idempotent stage: run the same stage twice")
stage_src = (
    "import bpy\n"
    "with kit.stage('selftest_cubes') as st:\n"
    "    for i in range(3):\n"
    "        me = bpy.data.meshes.new('c%d' % i)\n"
    "        me.from_pydata([(0,0,0),(1,0,0),(1,1,0),(0,1,0)], [], [(0,1,2,3)])\n"
    "        ob = bpy.data.objects.new('SelfTest.C%d' % i, me)\n"
    "        bpy.context.scene.collection.objects.link(ob)\n"
    "        ob.location = (i*2, 8, 0)\n"
    "__result__ = st.report()\n")
print("   run 1:", bl.code(stage_src))
print("   run 2:", bl.code(stage_src))
print("   objects named SelfTest.*:",
      bl.code("import bpy\n"
              "__result__ = len([o for o in bpy.data.objects if o.name.startswith('SelfTest')])\n"))

print("8. guard: snapshot, simulate a viewport scale, detect and revert")
snap = bl.code("__result__ = kit.guard()['snapshot']\n")
bl.code("import bpy\n"
        "from mathutils import Vector\n"
        "f = 3.5\n"
        "P = Vector((0.0, 0.0, 0.0))\n"
        "for o in bpy.data.objects:\n"
        "    if o.name.startswith('SelfTest'):\n"
        "        o.location = P + (Vector(o.location) - P) * f\n"
        "        o.scale = (f, f, f)\n"
        "__result__ = 'scaled 3 objects by 3.5'\n")
rep = bl.code("__result__ = {k: v for k, v in kit.guard(fix=False).items() if k != 'snapshot'}\n")
print("   detected:", rep["scaled"], "scaled objects")

print("9. cleanup: stage teardown removes its own objects")
print(bl.code("with kit.stage('selftest_cubes'):\n    pass\n"
              "__result__ = len([o for o in __import__('bpy').data.objects "
              "if o.name.startswith('SelfTest')])\n"))

print("10. summary")
print(bl.code("__result__ = kit.summary()\n"))
