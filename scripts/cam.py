"""Reposition the hero camera. Params come from cam_cfg.txt: x,y,z,tx,ty,tz,lens,fstop"""
import os
import sys

import bpy

sys.settrace(None)
BASE = r"C:\path\to\blender-live-agent-build\scripts"
vals = [float(v) for v in open(os.path.join(BASE, "cam_cfg.txt"), encoding="utf-8").read().split(",")]
x, y, z, tx, ty, tz, lens, fstop = vals

cam = bpy.data.objects["HeroCam"]
tgt = bpy.data.objects["CamTarget"]
cam.scale = (1.0, 1.0, 1.0)      # a stray object scale silently acts as a zoom
cam.rotation_euler = (0.0, 0.0, 0.0)
cam.location = (x, y, z)
tgt.location = (tx, ty, tz)
cam.data.lens = lens
cam.data.dof.aperture_fstop = fstop
bpy.context.view_layer.update()
__result__ = {"cam": tuple(cam.location), "target": tuple(tgt.location), "lens": lens}
print(__result__)
