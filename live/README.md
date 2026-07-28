# live — the Blender side, the camera, and the checks

`agentkit/` gives you the client half of the bridge. This folder adds the half
that was missing — the server that runs inside Blender — plus the machinery
that turned out to matter once a build ran long enough to be filmed: a camera
that shows what is being added, and checks that answer questions a render
cannot.

Everything here was written while building a 34 m pirate ship, ~1400 objects
over 50 stages, and every rule below is one that cost time before it was
written down.

## Run it

```bash
blender --factory-startup empty.blend --python live/bridge.py
python live/agent.py exec live/checks/safe_camera.py    # once, after launch
python live/play.py "stages/s*.py"
```

Make `empty.blend` once with a background Blender that deletes everything and
saves; opening a file also suppresses the splash.

`bridge.py` listens on 127.0.0.1:9876 with the same newline-delimited JSON the
`agentkit` client speaks, runs submitted code on Blender's **main thread** via
`bpy.app.timers` so the viewport updates live, collapses the window to a single
fullscreen 3D viewport, and adds:

* **hud** — a strip along the bottom that types out the code as it runs;
* **director** — a permanent slow orbit that eases onto whatever is being
  added and returns to a wide shot afterwards.

`checks/safe_camera.py` wraps the director so the eye is pushed out of a
keep-out box around the subject, close-ups pull back on their own, and
`director.timescale` shrinks every camera move when the build is replayed fast.

**Pauses belong to the client.** A `time.sleep` inside submitted code freezes
the main thread and the camera stops dead; `play.py` holds the dwell instead.

## Stage files

```python
#@title cannon — turning the barrel
#@note breech, reinforce rings, muzzle swell, bore
#@dwell 10
```

One idea per stage. Wrap the body in `plib.stage("name")` so a re-run deletes
what the previous run of that stage made — every stage stays repeatable after a
fix. Never consume another stage's objects: joining the cannon parts into one
mesh made that stage non-repeatable and broke the next run.

## The checks

A screenshot only shows what happens to face the camera. These do not.

| script | question |
|---|---|
| `checks/check_clash.py` | which meshes actually intersect, minus an allowlist of contacts that are correct (a sail bent to its yard, a mast through a deck, a gun in its port) |
| `checks/check_final.py` | is the hull closed where parts meet; is anything floating with nothing near it; does every rope end land on something |
| `check.py audit` | a 3×3 contact sheet of nine angles, for when you do want eyes on it |

### Why the first versions of these lied

* `BVHTree.FromObject` builds in the object's **local** space, so two objects
  with different transforms are compared in unrelated coordinate systems — it
  invents clashes and hides real ones. Build with `FromPolygons` over
  world-space vertices.
* `find_nearest` returns the object's **own** surface first, so "distance to
  anything else" is always ~0 and every part looks attached. Use
  `find_nearest_range` and drop hits inside that object's own triangle span.
* Vertices alone are not enough: a tapered spar has geometry only at its two
  end rings, and the part that touches something is the middle. Sample face
  centres too.
* If the scene is animated, stop playback and cache every world matrix before
  measuring — a rocking hull re-evaluates mid-loop and every number is noise.
* Compare like with like: model-space helpers versus world-space trees needs
  the root's matrix in between.

## Blender traps

* **Mix node in RGBA mode:** `node.inputs['A']` resolves to the *float* A — the
  colour sockets share the name — and links into a disabled socket are silently
  dropped, so the material quietly renders default grey. Resolve by name **and**
  `enabled` (`plib.sock`).
* **Solidify with `use_even_offset=True`** fires a spike tens of metres long
  from any near-degenerate vertex, and every lofted cap has one.
* **`(-0.07) ** 2.2` is a complex number** in Python; `from_pydata` then fails
  with "couldn't access the py sequence". Clamp before fractional powers.
* **A rectangular sweep is not a mast.** Round stock needs a circular section
  (`plib.spar`); `plib.sweep` is for keels, rails and beams.
* **Cambered decks:** a deck crowns towards the centreline, so anything placed
  at the nominal flat height sinks into the planking — capstan, hatches,
  barrels, gun trucks. Give yourself a `deck_z(deck, y)` helper.
* **Anything crossing an opening must be split**, not just the planking:
  wales, mouldings, inner bulwark, and any strake that merely *overlaps* the
  band rather than sitting fully inside it. A decorative strip running the whole
  length is the usual culprit when something "passes through a beam".

## Recording and the film

* `rec.py` captures the Blender **window** through Windows Graphics Capture.
  `gdigrab -i desktop` grabs the whole virtual desktop and will record the
  user's other monitor; `gdigrab -i title=` does not work for a
  GPU-composited window either.
* A replay must start from an **empty scene**, or the previous model is already
  standing there and the build looks instantaneous.
* Set `director.timescale` to the replay speed: stages ask for eight-second
  camera moves, and at a fast replay the camera never arrives.
* `make_film.py` records two passes — build, then launch and tour — and
  compresses only the build. Keep the raw passes; they are the original.
* **Interior shots are cuts, not moves.** Flying the camera inside drags it
  through the planking. Cut in, hold, cut out — and hold longer than feels
  right: the viewport draws slower down there, the capture collects fewer
  frames, and a normally-timed shot collapses to nothing.
* Put the interior eye in the actual free space, between the deck underfoot and
  the beams overhead, and off the centreline or a mast fills the frame.

## Look

EEVEE Next needs shadows asked for explicitly (`scene.eevee.use_shadows`).
Water is only as good as what it reflects: a Nishita sky alone is a smooth
gradient, and mirror-flat water under it renders as featureless white. A
procedural cloud deck in the world gives the sea its structure. Keep the ocean
modifier's foam coverage low — the default reads as a milky overcast surface.
