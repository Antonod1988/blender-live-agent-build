import os
import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())

OUT = r"C:\path\to\blender-live-agent-build\scripts\renders"
os.makedirs(OUT, exist_ok=True)
scn = bpy.context.scene

# ---- final grade: deeper sky, stronger key, warmer rim --------------------
nt = scn.world.node_tree
sky = next(n for n in nt.nodes if n.type == "TEX_SKY")
bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
sky.sun_elevation = math.radians(6.0)
sky.sun_rotation = math.radians(138.0)
sky.dust_density = 2.4
bg.inputs["Strength"].default_value = 0.44

sun = bpy.data.objects["SunKey"]
sun.rotation_euler = (math.radians(77.0), 0.0, math.radians(232.0))
sun.data.energy = 7.4
sun.data.color = (1.0, 0.70, 0.42)

fill = bpy.data.objects["SkyFill"]
fill.data.energy = 190.0

scn.view_settings.exposure = 0.05
scn.view_settings.look = "AgX - Medium High Contrast"
scn.render.image_settings.file_format = "PNG"
scn.render.image_settings.color_mode = "RGB"
scn.render.resolution_x, scn.render.resolution_y = 1920, 1080
try:
    scn.eevee.taa_render_samples = 192
except AttributeError:
    pass

cam = bpy.data.objects["HeroCam"]
tgt = bpy.data.objects["CamTarget"]
cam.scale = (1.0, 1.0, 1.0)

SHOTS = [
    ("final_01_hero", (10.4, -7.4, 2.00), (0.45, 0.10, 1.32), 45.0, 3.2),
    ("final_02_rear", (-7.2, -6.0, 2.35), (-0.30, 0.05, 1.45), 55.0, 3.6),
    ("final_03_detail", (3.55, -3.30, 1.28), (-0.10, -0.70, 1.42), 85.0, 2.2),
    ("final_04_front", (6.2, 1.9, 1.55), (0.60, 0.00, 1.40), 50.0, 3.2),
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
    done.append((tag, os.path.getsize(path) if os.path.exists(path) else 0))

__result__ = {"renders": done}
print(__result__)
