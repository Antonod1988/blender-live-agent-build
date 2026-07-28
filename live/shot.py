"""Grab the Blender window as a PNG so the agent can look at it."""
import sys
from agent import Blender

path = sys.argv[1] if len(sys.argv) > 1 else r"D:\pythonProject4\pirate-ship\shots\view.png"
code = (
    "import bpy, os\n"
    "os.makedirs(os.path.dirname(r'%s'), exist_ok=True)\n"
    "bpy.ops.screen.screenshot(filepath=r'%s')\n"
    "__result__ = r'%s'\n" % (path, path, path)
)
print(Blender().code(code, load_libs=False))
