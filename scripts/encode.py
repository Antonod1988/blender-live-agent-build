"""Assemble one MP4: sped-up build timelapse (~40 s) + real-time fly-through. No audio."""
import os
import sys

import bpy

sys.settrace(None)

BASE = r"C:\path\to\blender-live-agent-build\scripts"
FRAMES_DIR = os.path.join(BASE, "rec", "frames")
FLY_DIR = os.path.join(BASE, "renders", "fly")
OUT_FILE = os.path.join(BASE, "renders", "carriage_build.mp4")

FPS = 25
TIMELAPSE_SECONDS = 40

tl = sorted(f for f in os.listdir(FRAMES_DIR) if f.endswith(".jpg"))
target = FPS * TIMELAPSE_SECONDS
step = max(1, len(tl) // target)
tl_sel = tl[::step][:target]

fly = sorted(f for f in os.listdir(FLY_DIR) if f.endswith(".jpg")) if os.path.isdir(FLY_DIR) else []

scn = bpy.data.scenes.get("EncodeScene")
if scn:
    bpy.data.scenes.remove(scn)
scn = bpy.data.scenes.new("EncodeScene")
scn.render.fps = FPS
scn.render.resolution_x, scn.render.resolution_y = 1280, 720
scn.render.resolution_percentage = 100
scn.sequence_editor_create()
se = scn.sequence_editor

start = 1
if tl_sel:
    s1 = se.sequences.new_image("timelapse", os.path.join(FRAMES_DIR, tl_sel[0]), 1, start)
    for name in tl_sel[1:]:
        s1.elements.append(name)
    s1.frame_final_duration = len(tl_sel)
    for attr, val in (("use_fit", True),):
        if hasattr(s1, attr):
            setattr(s1, attr, val)
    if hasattr(s1, "transform"):
        s1.transform.scale_x = 1.0
        s1.transform.scale_y = 1.0
    start += len(tl_sel)

if fly:
    s2 = se.sequences.new_image("flythrough", os.path.join(FLY_DIR, fly[0]), 2, start)
    for name in fly[1:]:
        s2.elements.append(name)
    s2.frame_final_duration = len(fly)
    start += len(fly)

scn.frame_start = 1
scn.frame_end = max(1, start - 1)
scn.render.use_sequencer = True
scn.render.image_settings.file_format = "FFMPEG"
scn.render.ffmpeg.format = "MPEG4"
scn.render.ffmpeg.codec = "H264"
scn.render.ffmpeg.constant_rate_factor = "MEDIUM"
scn.render.ffmpeg.ffmpeg_preset = "GOOD"
scn.render.ffmpeg.gopsize = 25
scn.render.ffmpeg.audio_codec = "NONE"
scn.render.filepath = OUT_FILE

bpy.ops.render.render(animation=True, scene=scn.name)

made = [f for f in os.listdir(os.path.dirname(OUT_FILE))
        if f.startswith("carriage_build") and f.endswith(".mp4")]
__result__ = {
    "timelapse_source_frames": len(tl), "step": step, "timelapse_frames": len(tl_sel),
    "fly_frames": len(fly), "total_frames": scn.frame_end, "fps": FPS,
    "seconds": round(scn.frame_end / FPS, 1),
    "files": {f: round(os.path.getsize(os.path.join(os.path.dirname(OUT_FILE), f)) / 1e6, 1)
              for f in made},
}
print(__result__)
