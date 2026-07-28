"""Pacer: plays stage files into the live Blender session, slowly.

Each stage file may carry a header:

    #@title Cannons - barrel
    #@note turning the profile
    #@dwell 7

The dwell is spent sleeping on THIS side, so Blender's main thread stays free
and the camera keeps moving while nothing is being built.

    python play.py stages/s0*.py
    python play.py --speed 0.4 stages/s12_*.py     # rehearse quickly
"""

from __future__ import annotations

import glob
import os
import sys
import time

from agent import Blender, BlenderError


def header(src):
    meta = {"title": None, "note": "", "dwell": 4.0}
    for ln in src.splitlines():
        s = ln.strip()
        if not s.startswith("#@"):
            if s and not s.startswith("#"):
                break
            continue
        key, _, val = s[2:].partition(" ")
        key = key.strip().lower()
        val = val.strip()
        if key == "title":
            meta["title"] = val
        elif key == "note":
            meta["note"] = val
        elif key == "dwell":
            meta["dwell"] = float(val)
    return meta


def main(argv):
    speed = 1.0
    files = []
    i = 0
    while i < len(argv):
        if argv[i] == "--speed":
            speed = float(argv[i + 1])
            i += 2
            continue
        files.extend(sorted(glob.glob(argv[i])))
        i += 1
    if not files:
        print("no stage files matched")
        return 1

    bl = Blender()
    if not bl.wait_alive(20):
        print("bridge is not answering on 127.0.0.1:9876 - is Blender running?")
        return 2

    # the camera has to move at the pace the stages are played, or it is still
    # travelling to the last part when three more have appeared
    try:
        bl.code("director.timescale = %f\n__result__ = 1\n" % speed,
                load_libs=False)
    except BlenderError:
        pass

    t0 = time.time()
    for path in files:
        with open(path, encoding="utf-8") as f:
            src = f.read()
        meta = header(src)
        title = meta["title"] or os.path.basename(path)
        print("[%6.1fs] %-46s" % (time.time() - t0, title), end="", flush=True)
        try:
            res = bl.code(src, hud_code=src, title=title, note=meta["note"])
        except BlenderError as exc:
            print("  FAILED")
            print(str(exc)[-2500:])
            return 3
        print("  ok %s" % ("" if res is None else str(res)[:90]))
        time.sleep(max(0.0, meta["dwell"] * speed))
    print("done in %.1fs" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
