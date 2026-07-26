"""Cinematic fly-through: hub -> springs -> door crest -> lantern -> roof -> pole -> wide."""
import math
import os
import shutil
import sys

import bpy

sys.settrace(None)

BASE = r"C:\path\to\blender-live-agent-build\scripts"
OUT = os.path.join(BASE, "renders", "fly")
if os.path.isdir(OUT):
    shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT, exist_ok=True)

scn = bpy.context.scene
cam = bpy.data.objects["HeroCam"]
tgt = bpy.data.objects["CamTarget"]
cam.animation_data_clear()
tgt.animation_data_clear()
cam.data.animation_data_clear()
cam.scale = (1.0, 1.0, 1.0)
cam.data.dof.use_dof = True
cam.data.dof.focus_object = tgt

# frame, camera position, look-at, lens, f-stop
POSES = [
    (1,   (10.4, -7.40, 2.00), (0.45,  0.10, 1.32), 45.0, 4.0),   # establishing wide
    (55,  (4.90, -2.95, 0.86), (1.46, -0.92, 0.50), 62.0, 2.8),   # front hub & spokes
    (110, (0.60, -3.20, 0.80), (-0.60, -1.00, 0.72), 55.0, 3.0),  # springs and perch
    (165, (1.05, -2.95, 1.42), (-0.19, -0.72, 1.34), 82.0, 2.2),  # door crest
    (215, (2.75, -2.45, 1.92), (1.20, -0.74, 1.83), 70.0, 2.6),   # lantern
    (265, (2.40, -1.55, 3.20), (-0.30,  0.00, 2.44), 40.0, 4.0),  # over the roof rail
    (315, (-5.30, -2.10, 2.35), (-0.80,  0.00, 1.58), 45.0, 4.5), # rear quarter
    (365, (-4.40,  3.60, 1.95), (-0.50,  0.30, 1.50), 50.0, 4.5), # off side
    (415, (5.60,  3.30, 1.20), (2.60,  0.35, 0.80), 55.0, 3.2),   # along the pole
    (470, (9.90, -2.60, 2.25), (1.10,  0.00, 1.35), 42.0, 4.5),   # settle wide
]

for f, loc, trg, lens, fstop in POSES:
    cam.location = loc
    tgt.location = trg
    cam.data.lens = lens
    cam.data.dof.aperture_fstop = fstop
    cam.keyframe_insert("location", frame=f)
    tgt.keyframe_insert("location", frame=f)
    cam.data.keyframe_insert("lens", frame=f)
    cam.data.dof.keyframe_insert("aperture_fstop", frame=f)

for holder in (cam, tgt, cam.data):
    ad = holder.animation_data
    if ad and ad.action:
        for fc in ad.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
            fc.update()

scn.frame_start, scn.frame_end = 1, POSES[-1][0]
scn.render.fps = 30
scn.render.resolution_x, scn.render.resolution_y = 1280, 720
try:
    scn.eevee.taa_render_samples = 32
except AttributeError:
    pass
scn.render.image_settings.file_format = "JPEG"
scn.render.image_settings.quality = 92
scn.render.image_settings.color_mode = "RGB"
scn.render.filepath = os.path.join(OUT, "fly_")
bpy.ops.render.render(animation=True)

files = sorted(f for f in os.listdir(OUT) if f.endswith(".jpg"))
__result__ = {"frames": len(files), "dir": OUT,
              "mb": round(sum(os.path.getsize(os.path.join(OUT, f)) for f in files) / 1e6, 1)}
print(__result__)
