"""Four-angle contact sheet: catch a bug before it is buried under the next stage.

    python check.py bow          # or: side, top, all (default)

One render can hide anything. Four cheap ones, tiled, cannot.
"""

import os
import subprocess
import sys
import time

import imageio_ffmpeg

from agent import Blender

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "shots")
FF = imageio_ffmpeg.get_ffmpeg_exe()

# az 0 puts the eye off the port beam; +90 dead ahead; -90 dead astern
VIEWS = {
    "bow":   dict(az=68.0, elev=12.0, dist=26.0, t=(8.0, 0.0, 4.0)),
    "beam":  dict(az=0.0, elev=8.0, dist=38.0, t=(0.0, 0.0, 5.0)),
    "quarter": dict(az=-48.0, elev=15.0, dist=30.0, t=(-6.0, 0.0, 4.5)),
    "stern": dict(az=-90.0, elev=6.0, dist=17.0, t=(-14.0, 0.0, 3.6)),
    "top":   dict(az=-40.0, elev=58.0, dist=36.0, t=(0.0, 0.0, 2.0)),
    # the three spots that keep going wrong
    "gundeck": dict(az=64.0, elev=4.0, dist=7.0, t=(-1.0, 2.2, 1.5)),
    "channel": dict(az=2.0, elev=6.0, dist=9.0, t=(0.5, 4.4, 2.7)),
    "flag":    dict(az=-104.0, elev=2.0, dist=9.0, t=(-1.2, 0.0, 28.4)),
    "portslow": dict(az=8.0, elev=-6.0, dist=16.0, t=(-1.0, 0.0, 2.4)),
}

AUDIT = [
    ("wide.bow", dict(az=-40.0, elev=15.0, dist=40.0, t=(2.0, 0.0, 6.0))),
    ("wide.beam", dict(az=-92.0, elev=9.0, dist=44.0, t=(0.0, 0.0, 7.0))),
    ("wide.stern", dict(az=148.0, elev=15.0, dist=40.0, t=(-4.0, 0.0, 6.0))),
    ("close.bow", dict(az=-28.0, elev=7.0, dist=14.0, t=(13.5, 0.0, 3.2))),
    ("close.ports", dict(az=-96.0, elev=11.0, dist=21.0, t=(0.0, 0.0, 2.2))),
    ("close.stern", dict(az=166.0, elev=9.0, dist=14.0, t=(-14.0, 0.0, 3.6))),
    ("close.waist", dict(az=-72.0, elev=32.0, dist=15.0, t=(1.0, 0.0, 3.0))),
    ("close.wheel", dict(az=152.0, elev=25.0, dist=12.0, t=(-5.2, 0.0, 4.6))),
    ("close.tops", dict(az=-58.0, elev=20.0, dist=20.0, t=(0.0, 0.0, 15.0))),
]

SNAP = """
import bpy
director.enabled = True
director._focus_raw(target=(%f, %f, %f), dist=%f, elev=%f, az=%f, secs=0.01)
__result__ = 'set'
"""

GRAB = """
import bpy, os
os.makedirs(os.path.dirname(r'%s'), exist_ok=True)
bpy.ops.screen.screenshot(filepath=r'%s')
__result__ = 1
"""


def audit():
    bl = Blender()
    root_z = bl.code("import bpy\n__result__ = bpy.data.objects['ShipRoot'].location.z\n",
                     load_libs=False) or 0.0
    files = []
    for name, v in AUDIT:
        bl.code(SNAP % (v["t"][0], v["t"][1], v["t"][2] + root_z,
                        v["dist"], v["elev"], v["az"]), load_libs=False)
        time.sleep(1.1)
        p = os.path.join(SHOTS, "aud_%s.png" % name.replace(".", "_"))
        bl.code(GRAB % (p, p), load_libs=False)
        files.append(p)
    out = os.path.join(SHOTS, "audit.png")
    cmd = [FF, "-y", "-loglevel", "error"]
    for f in files:
        cmd += ["-i", f]
    parts = ";".join("[%d:v]scale=760:-1[v%d]" % (i, i) for i in range(9))
    parts += ";[v0][v1][v2]hstack=inputs=3[r0]"
    parts += ";[v3][v4][v5]hstack=inputs=3[r1]"
    parts += ";[v6][v7][v8]hstack=inputs=3[r2]"
    parts += ";[r0][r1][r2]vstack=inputs=3"
    cmd += ["-filter_complex", parts, "-frames:v", "1", out]
    subprocess.run(cmd, check=True)
    print(out)


def main(argv):
    if argv and argv[0] == "audit":
        return audit()
    names = [a for a in argv if a in VIEWS] or list(VIEWS)
    bl = Blender()
    root_z = bl.code("import bpy\n__result__ = bpy.data.objects['ShipRoot'].location.z\n",
                     load_libs=False) or 0.0
    files = []
    for n in names:
        v = VIEWS[n]
        bl.code(SNAP % (v["t"][0], v["t"][1], v["t"][2] + root_z,
                        v["dist"], v["elev"], v["az"]), load_libs=False)
        time.sleep(1.1)
        p = os.path.join(SHOTS, "chk_%s.png" % n)
        bl.code(GRAB % (p, p), load_libs=False)
        files.append(p)

    out = os.path.join(SHOTS, "check.png")
    cmd = [FF, "-y", "-loglevel", "error"]
    for f in files:
        cmd += ["-i", f]
    if len(files) == 1:
        flt = "[0:v]scale=1400:-1"
    elif len(files) == 4:
        flt = ("[0:v]scale=900:-1[a];[1:v]scale=900:-1[b];[2:v]scale=900:-1[c];"
               "[3:v]scale=900:-1[d];[a][b]hstack[t];[c][d]hstack[u];[t][u]vstack")
    else:
        flt = ";".join("[%d:v]scale=900:-1[v%d]" % (i, i) for i in range(len(files)))
        flt += ";" + "".join("[v%d]" % i for i in range(len(files)))
        flt += "hstack=inputs=%d" % len(files)
    cmd += ["-filter_complex", flt, "-frames:v", "1", out]
    subprocess.run(cmd, check=True)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1:])
