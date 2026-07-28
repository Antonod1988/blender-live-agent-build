"""Record the Blender window itself - not whatever happens to be on screen.

Windows Graphics Capture grabs the window's own composited surface, so other
windows on top, or Blender being on a second monitor, do not end up in the
film. Frames are halved in numpy (cheap) and piped to x264, which keeps a
long build session in the tens of megabytes.

    python rec.py start     # blocks; launch it detached
    python rec.py stop      # drops the sentinel, ffmpeg closes the file cleanly
"""

import os
import subprocess
import sys
import time

import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
FF = imageio_ffmpeg.get_ffmpeg_exe()
OUT = os.path.join(HERE, "build.mp4")
FLAG = os.path.join(HERE, ".rec.stop")
WINDOW = "Blender 4.3.2"
FPS = 12


def _encoder(w, h, out, fps=FPS, crf=27):
    cmd = [
        FF, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgra", "-s", "%dx%d" % (w, h),
        "-framerate", str(fps), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
        "-crf", str(crf), "-g", "120", "-pix_fmt", "yuv420p",
        "-movflags", "+frag_keyframe+empty_moov",
        out,
    ]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def start(out=OUT):
    from windows_capture import WindowsCapture

    if os.path.exists(FLAG):
        os.remove(FLAG)
    state = {"proc": None, "last": 0.0, "n": 0}

    cap = WindowsCapture(cursor_capture=False, draw_border=False,
                         window_name=WINDOW)

    @cap.event
    def on_frame_arrived(frame, control):
        now = time.time()
        if now - state["last"] < 1.0 / FPS:
            return
        state["last"] = now
        buf = frame.frame_buffer[::2, ::2]           # half size, cheap
        if state["proc"] is None:
            h, w = buf.shape[0], buf.shape[1]
            state["proc"] = _encoder(w, h, out)
            print("recording %dx%d -> %s" % (w, h, out))
        try:
            state["proc"].stdin.write(buf.tobytes())
        except Exception:
            control.stop()
            return
        state["n"] += 1
        if os.path.exists(FLAG):
            control.stop()

    @cap.event
    def on_closed():
        pass

    try:
        cap.start()
    except KeyboardInterrupt:
        pass
    p = state["proc"]
    if p is not None:
        try:
            p.stdin.close()
        except Exception:
            pass
        p.wait(timeout=60)
    if os.path.exists(FLAG):
        os.remove(FLAG)
    size = os.path.getsize(out) / 1e6 if os.path.exists(out) else 0
    print("stopped after %d frames, %.1f MB" % (state["n"], size))


def stop():
    open(FLAG, "w").close()
    for _ in range(80):
        if not os.path.exists(FLAG):
            break
        time.sleep(0.5)
    print("stop requested")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "start"
    if arg == "stop":
        stop()
    else:
        start(sys.argv[2] if len(sys.argv) > 2 else OUT)
