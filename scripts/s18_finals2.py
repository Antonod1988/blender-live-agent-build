"""Re-shoot the hero stills against the finished model (crest + gem fixes included)."""
import math
import os
import sys

import bpy

sys.settrace(None)

OUT = r"C:\path\to\blender-live-agent-build\scripts\renders"
os.makedirs(OUT, exist_ok=True)
scn = bpy.data.scenes.get("Scene") or bpy.context.scene
bpy.context.window.scene = scn

cam = bpy.data.objects["HeroCam"]
tgt = bpy.data.objects["CamTarget"]

# the fly-through left keyframes on both - they would override any pose we set
cam.animation_data_clear()
tgt.animation_data_clear()
if cam.data.animation_data:
    cam.data.animation_data_clear()
cam.scale = (1.0, 1.0, 1.0)
cam.rotation_euler = (0.0, 0.0, 0.0)
cam.data.dof.use_dof = True
cam.data.dof.focus_object = tgt

scn.render.use_sequencer = False
scn.render.image_settings.file_format = "PNG"
scn.render.image_settings.color_mode = "RGB"
scn.render.image_settings.compression = 15
scn.render.resolution_x, scn.render.resolution_y = 1920, 1080
scn.render.resolution_percentage = 100
scn.render.film_transparent = False
try:
    scn.eevee.taa_render_samples = 224
except AttributeError:
    pass
scn.view_settings.view_transform = "AgX"
scn.view_settings.look = "AgX - Medium High Contrast"
scn.view_settings.exposure = 0.05

SHOTS = [
    ("final_01_hero",   (10.4, -7.40, 2.00), (0.45,  0.10, 1.32), 45.0, 4.0),
    ("final_02_rear",   (-7.2, -6.00, 2.35), (-0.30, 0.05, 1.45), 55.0, 3.6),
    ("final_03_detail", (2.30, -3.05, 1.44), (-0.19, -0.72, 1.28), 62.0, 2.6),
    ("final_04_front",  (6.20,  1.90, 1.55), (0.60,  0.00, 1.40), 50.0, 3.2),
    ("final_05_wheel",  (4.90, -2.95, 0.86), (1.46, -0.92, 0.50), 62.0, 2.8),
]
done = []
for tag, loc, trg, lens, fstop in SHOTS:
    cam.location = loc
    tgt.location = trg
    cam.data.lens = lens
    cam.data.dof.aperture_fstop = fstop
    bpy.context.view_layer.update()
    path = os.path.join(OUT, tag + ".png")
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    done.append((tag, round(os.path.getsize(path) / 1e6, 2) if os.path.exists(path) else 0))

__result__ = {"renders": done, "samples": getattr(scn.eevee, "taa_render_samples", None)}
print(__result__)
