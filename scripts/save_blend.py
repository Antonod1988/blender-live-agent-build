import os
import sys

import bpy

sys.settrace(None)

DEST = r"C:\path\to\blender-live-agent-build\output"
os.makedirs(DEST, exist_ok=True)
path = os.path.join(DEST, "fantasy_carriage.blend")

# restore sane render settings before saving
scn = bpy.data.scenes.get("Scene") or bpy.context.scene
scn.render.image_settings.file_format = "PNG"
scn.render.resolution_x, scn.render.resolution_y = 1920, 1080
scn.frame_current = 1

enc = bpy.data.scenes.get("EncodeScene")
if enc:
    bpy.data.scenes.remove(enc)

bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
__result__ = {"blend": path, "mb": round(os.path.getsize(path) / 1e6, 1),
              "objects": len(bpy.data.objects)}
print(__result__)
