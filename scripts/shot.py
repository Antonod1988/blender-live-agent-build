"""Render a preview still. Tag + resolution are read from a side-car file."""
import os
import sys

import bpy

sys.settrace(None)

BASE = r"C:\path\to\blender-live-agent-build\scripts"
OUT = os.path.join(BASE, "renders")
os.makedirs(OUT, exist_ok=True)

with open(os.path.join(BASE, "shot_cfg.txt"), encoding="utf-8") as f:
    tag, w, h, samples = f.read().strip().split(",")

scn = bpy.context.scene
scn.render.image_settings.file_format = "PNG"
scn.render.image_settings.color_mode = "RGB"
scn.render.resolution_x, scn.render.resolution_y = int(w), int(h)
try:
    scn.eevee.taa_render_samples = int(samples)
except AttributeError:
    pass
path = os.path.join(OUT, tag + ".png")
scn.render.filepath = path
bpy.ops.render.render(write_still=True)
__result__ = {"path": path, "size": os.path.getsize(path) if os.path.exists(path) else 0}
print(__result__)
