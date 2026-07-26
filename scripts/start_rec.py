import os
import bpy

OUT = r"C:\path\to\blender-live-agent-build\scripts\rec\frames"
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    try:
        os.remove(os.path.join(OUT, f))
    except OSError:
        pass

ns = bpy.app.driver_namespace
ns["mcp_rec"] = {"i": 0, "on": True, "dir": OUT, "errors": []}

INTERVAL = 0.55


def _grab():
    st = bpy.app.driver_namespace.get("mcp_rec")
    if not st or not st["on"]:
        return None
    try:
        scn = bpy.context.scene
        img = scn.render.image_settings
        old = (img.file_format, img.quality, img.color_mode)
        img.file_format = "JPEG"
        img.quality = 80
        img.color_mode = "RGB"
        path = os.path.join(st["dir"], "f%06d.jpg" % st["i"])
        bpy.ops.screen.screenshot(filepath=path)
        img.file_format, img.quality, img.color_mode = old
        st["i"] += 1
    except Exception as exc:  # keep the timelapse alive through transient failures
        if len(st["errors"]) < 5:
            st["errors"].append(repr(exc))
    return INTERVAL


for t in list(bpy.app.timers.__dir__()):
    pass
if bpy.app.timers.is_registered(_grab):
    bpy.app.timers.unregister(_grab)
ns["mcp_rec_fn"] = _grab
bpy.app.timers.register(_grab, first_interval=0.1)

__result__ = {"recording": True, "dir": OUT, "interval": INTERVAL}
