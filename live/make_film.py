"""Record the film in two passes and cut it to under a minute.

Pass 1 is the build, replayed fast. Pass 2 is the launch and the flythrough at
their real speed. The build is then compressed so the whole thing lands near
sixty seconds with the closing move still readable.
"""

import os
import subprocess
import sys
import time

import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
FF = imageio_ffmpeg.get_ffmpeg_exe()
PY = sys.executable
BUILD = os.path.join(HERE, "raw_build.mp4")
FINAL = os.path.join(HERE, "raw_final.mp4")
OUT = os.path.join(HERE, "pirate_ship.mp4")
TARGET_BUILD = 20.0        # the build is a timelapse; the flythrough is the film
KEEP_RAW = True            # keep the full-speed passes; they are the original


def run(*args):
    subprocess.run([PY] + list(args), cwd=HERE, check=False)


def rec_start(path):
    subprocess.Popen([PY, "rec.py", "start", path], cwd=HERE,
                     creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(3.0)


def rec_stop():
    run("rec.py", "stop")
    time.sleep(4.0)


def duration(path):
    out = subprocess.run([FF, "-i", path], capture_output=True, text=True).stderr
    for line in out.splitlines():
        if "Duration:" in line:
            h, m, s = line.split("Duration:")[1].split(",")[0].strip().split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


KEEP = "--keep-build" in sys.argv
for p in ((FINAL,) if KEEP else (BUILD, FINAL)):
    if os.path.exists(p):
        os.remove(p)

if KEEP and os.path.exists(BUILD):
    print("pass 1 - reusing the build already on disk")
else:
    print("pass 1 - the build")
    rec_start(BUILD)
    run("play.py", "--speed", "0.12", "stages/s00_clear.py",
        "stages/s0[1-9]*.py", "stages/s[1-4]*.py")
    rec_stop()

print("pass 2 - launch and flythrough")
run("agent.py", "exec", "tools/reset_stocks.py")
time.sleep(1.5)
rec_start(FINAL)
run("play.py", "stages/s51_launch.py", "stages/s52_physics.py")
run("fly.py", "--short")
rec_stop()

db, df = duration(BUILD), duration(FINAL)
speed = max(1.0, db / TARGET_BUILD)
print("build %.1fs -> %.1fs (x%.2f), closing %.1fs" % (db, db / speed, speed, df))

subprocess.run([
    FF, "-y", "-loglevel", "error", "-i", BUILD, "-i", FINAL,
    "-filter_complex",
    "[0:v]setpts=PTS/%.3f,fps=24[a];[1:v]fps=24[b];[a][b]concat=n=2:v=1[v]" % speed,
    "-map", "[v]", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT,
], check=True)

if not KEEP_RAW:
    for p in (BUILD, FINAL):
        if os.path.exists(p):
            os.remove(p)
print("%s  %.1f s  %.1f MB" % (OUT, duration(OUT), os.path.getsize(OUT) / 1e6))
