"""Closing flythrough: walk the camera over every part of the finished ship.

Pacing lives here, on the client, so Blender's main thread stays free and the
move itself is smooth.
"""

import sys
import time

from agent import Blender

MOVE = """
director.orbit(%f)
director._focus_raw(target=(%f, %f, %f), dist=%f, elev=%f, az=%f, secs=%f)
__result__ = 1
"""

# close shots go through the guarded mover so the eye never ends up inside
CLOSE = """
director.orbit(%f)
director.detail((%f, %f, %f), dist=%f, elev=%f, az=%f, secs=%f, hold=99.0)
__result__ = 1
"""

# label, target, dist, elev, az, travel, hold, orbit
SHOTS = [
    ("she floats",        (0, 0, 4.0),    54, 10, -118, 8, 3, 3.0),
    ("bow and bowsprit",  (14.5, 0, 4.5), 19, 8,  -34,  7, 3, 2.2),
    ("anchor at the cathead", (12.0, 3.4, 2.4), 11, 4, -52, 6, 3, 1.6),
    ("the gun deck ports", (-2.0, 4.6, 1.8), 15, 3, -96, 7, 3, 1.6),
    ("waist battery",     (5.0, 3.0, 3.0), 12, 12, -74, 6, 3, 1.8),
    ("capstan and hatches", (-1.0, 0, 2.9), 13, 30, -110, 6, 3, 2.0),
    ("up the shrouds",    (0.0, 3.2, 8.0), 17, 14, -84, 7, 3, 2.0),
    ("the maintop",       (-0.6, 0, 14.6), 14, 8, -140, 7, 3, 2.0),
    ("courses and topsails", (2.0, 0, 12.0), 34, 6, -150, 8, 3, 2.4),
    ("the black flag",    (-1.4, 0, 28.5), 13, 4, -170, 6, 3, 1.8),
    ("quarterdeck and wheel", (-5.2, 0, 4.8), 13, 22, 150, 7, 3, 1.8),
    ("stern lanterns",    (-14.5, 0, 5.6), 12, 8, 172, 6, 3, 1.6),
    ("the transom",       (-15.0, 0, 2.6), 17, 6, 158, 7, 3, 1.8),
    ("under her lee",     (0, 0, 5.0),     40, 4, 96,  9, 4, 2.6),
    ("full sail",         (1.0, 0, 8.0),   58, 12, 20, 10, 6, 3.4),
]


# label, target, dist, elev, az, travel, hold, orbit, close
#
# An unhurried tour: long eases, real holds, and the angle changing between
# shots so it never reads as one continuous orbit. `close` runs the guarded
# mover, which keeps the eye outside the hull; the below-decks shots pass
# False on purpose, because they are allowed inside.
SHORT = [
    ("she sails",              (0, 0, 5.0),      56, 5, 150, 7.0, 2.5, 1.8, False),
    ("up the bow",             (14.4, 0, 4.0),   17, 4, 62,  6.0, 2.0, 1.0, True),
    ("bowsprit and jibs",      (20.0, 0, 7.0),   17, 8, 34,  5.5, 2.0, 0.9, True),
    ("anchor at the cathead",  (11.6, 3.0, 2.6),  9, 6, 22,  5.0, 2.0, 0.8, True),
    ("along her broadside",    (-1.0, 4.4, 2.1), 16, 1, 0,   7.0, 2.0, 0.8, True),
    ("channel and deadeyes",   (0.0, 4.6, 2.9),   9, 5, 10,  5.0, 2.0, 0.8, True),
    ("up the shrouds",         (0.0, 3.6, 8.5),  13, 12, -6, 6.0, 2.0, 0.9, True),
    ("the maintop",            (-0.9, 0, 14.7),  10, 3, -46, 6.0, 2.0, 0.9, True),
    ("yards and canvas",       (1.0, 0, 17.5),   19, 5, -104, 6.0, 2.0, 1.1, True),
    # beam-on and close: the flag streams along X, so any other angle sees it
    # edge-on and the skull never reads
    ("the Jolly Roger",        (1.6, 0, 28.6),    7, 0, -4, 6.0, 6.0, 0.5, True),
    ("her whole rig",          (0.0, 0, 13.0),   46, 16, -168, 6.0, 2.5, 1.6, False),
    ("down into the waist",    (1.0, 0, 3.4),    13, 34, -66, 6.0, 2.0, 0.9, True),
    ("guns, shot and capstan", (1.5, 1.6, 3.0),   9, 14, -26, 5.5, 2.5, 0.8, True),
    # Below decks these are CUTS, not moves: flying the camera in would drag
    # it through the planking. The eye must clear the beams overhead
    # (1.67-1.93) and the deck underfoot (0.62), so it rides at about 1.5, and
    # off the centreline or the mainmast sits dead in the middle. They hold
    # longer too: the viewport draws slower down there, the capture collects
    # fewer frames, and a normally-timed shot collapses to nothing in the cut.
    ("down on the gun deck",   (-3.0, 1.5, 1.15), 11, 2, 90,  0.5, 5.0, 0.3, False),
    ("a gun and its breeching", (3.2, 2.4, 1.30),  5, 2, 90,  0.5, 4.5, 0.2, False),
    ("forward along the guns", (2.0, -1.5, 1.15), 11, 2, -90, 0.5, 4.5, 0.3, False),
    ("the quarterdeck",        (-5.2, 0, 5.0),   12, 18, -134, 5.5, 2.0, 0.9, True),
    ("stern gallery and lights", (-15.6, 0, 4.2), 13, 3, -90, 6.0, 3.0, 0.9, True),
    ("her wake",               (-13.0, 0, 1.2),  26, 2, -70, 6.0, 2.5, 1.2, False),
    ("she sails on",           (1.0, 0, 7.0),    60, 9, 24, 12.0, 5.0, 2.2, False),
]


def main(speed=1.0, shots=None):
    bl = Blender()
    # the build may have left the camera scaled down to keep up with it
    bl.code("director.timescale = 1.0\n__result__ = 1\n", load_libs=False)
    for shot in (shots or SHOTS):
        label, t, dist, elev, az, travel, hold, orbit = shot[:8]
        close = shot[8] if len(shot) > 8 else False
        tmpl = CLOSE if close else MOVE
        bl.code(tmpl % (orbit, t[0], t[1], t[2], dist, elev, az, travel),
                load_libs=False, title="flythrough — %s" % label,
                note="the finished ship")
        print("  %-26s" % label, flush=True)
        time.sleep((travel + hold) * speed)
    print("flythrough done")


if __name__ == "__main__":
    args = sys.argv[1:]
    short = "--short" in args
    args = [a for a in args if not a.startswith("--")]
    main(float(args[0]) if args else 1.0, SHORT if short else None)
