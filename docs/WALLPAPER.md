# The wallpaper scene

Notes for anyone changing a number in `wallpaper/build/scene.py`. The scene is
generated, not hand-edited: run `prepare_images.py` then `build.py`, never edit
`wallpaper/index.html` directly.

## What was wrong with the first version

It was not short of motion — it had too much of the wrong kind, and none of it
on the subject.

- Every keyframe block was a symmetric ease-in-out, so everything decelerated to
  a dead stop twice per cycle: a pulse, not weather.
- `glow 8s` divided into `drift 40s` exactly five times, so the whole frame
  returned to an identical state **every 40 seconds** — long enough to notice,
  short enough to memorise.
- The painting's focal point, the sun and its specular column down the river,
  had no animation within 15% in any direction. All the movement was in the dark
  bottom-right corner, so the eye landed on the subject and found it dead.
- The brightest pixels in the frame were the wet foreground pavement, which
  out-punched the sunset at both ends of the histogram. The composition had no
  value hierarchy.
- Rain never landed. The whole mirror-wet promenade got two elliptical puddles
  with eight rings between them; the river got nothing.

## The three rules

1. **One camera law.** `.camera` is a static overscale. `.world` translates. The
   near plane is the only `scale` animation in the file. A continuously
   animating scale never lands on a stable sample grid, so every fine edge in a
   2.3×-upsampled painting crawls.
2. **Coprime periods.** No two large-area elements may share a prime factor.
   `tests/check.py` asserts this. The rain field now relocks every ~49 minutes
   instead of every 75 seconds.
3. **No dwell.** Element-level `animation-timing-function` is `linear`; the
   easing lives on **per-keyframe** timing functions, which apply per segment.
   Putting the bezier on the element is the bug an implementer hits first — it
   reintroduces a dwell at every stop.

## The motion budget

At any instant no more than ~12% of frame area may carry above-threshold motion.

**The sun's specular column owns the eye.** It is the painting's own focal
point, it survives every crop down to 21:9, and it is the only element permitted
a large-area luminance swing above 0.25. Everything else is support and stays
below half its local contrast. Traffic, impact field, boats and their light
columns together account for under 3% of the frame.

## Measured gates

`prepare_images.py` prints these and exits non-zero if they fail:

| gate | why |
|---|---|
| promenade p95 lands 120–130 (from 170) | the pavement must stop out-punching the sunset |
| promenade p05 stays ≤ 5 | blacks must not lift — that is the "gel over a painting" read |
| sky mean unchanged ±1 | the knockdown is for the foreground only |
| **sky p95 must exceed promenade p95** | the real gate: value hierarchy restored |

The grade is applied in **linear light**, with Oklab chroma scaled alongside
luminance. Compositing a flat dark colour in sRGB clips the speculars flat. And
`a`/`b` must follow `L`: Oklab chroma is absolute, so holding them fixed under a
dimmed `L` makes the pavement read as *more* saturated, not less.

## Two bugs worth not repeating

Both are now regression-tested in `tests/check.py`.

**The rain was invisible.** The SVG tiles reference their gradient as
`url(%23r)`. Writing the `#` pre-encoded and *then* percent-encoding the whole
SVG yields `%2523` — a dangling paint-server reference. Every drop renders with
no fill, and the rain silently disappears with no error anywhere.

**Reduce Motion turned the emitters into blobs.** Under `animation:none` an
element renders its *declared* value. `.emit` declared no `opacity`, so its
default of `1` applied and each glow became a solid disc. Any element whose
visible opacity comes only from keyframes needs a declared base — and that base
should be the time-weighted **mean** of the keyframes, not the floor. The
accessible path should be the best still frame in the file, not the dimmest.

## The near plane

The promenade is a second copy of the same image (same `CachedImage`, zero extra
bytes), bounded and scaled against the camera so the near field dollies while
the far field translates.

Its boundary is a **feathered mask, not a `clip-path`**. A hard clip was tried
and fails: the plane and the base are the same picture at different scales, so a
hard edge butts two copies offset by ~13px at the dolly extreme and the parapet
visibly steps. Feathering cross-dissolves them and the offset disappears.

The mask's `31.1deg` angle and `31.35%` stop centre are derived, not eyeballed.
`.world`'s aspect ratio is pinned at 3/2, so the painted parapet's two endpoints
— world (24%, 62%) and (66%, 100%) — both project to 31.35% along that gradient
line on *every* display.

## Crop behaviour

`.world` is bottom-anchored, so all overflow is thrown off the **top**: 6.25% at
16:10, 15.6% at 16:9, 35.7% at 21:9. Untreated, the sun ends up jammed under the
menu bar on a 4K external and gone entirely on an ultrawide.

- Between 3:2 and 1.85:1 the overflow is split rather than all taken off the top.
- Past 1.85:1 the world stops growing and is pillarboxed against a 1.2 KB, 64×43
  plate of itself. The browser's upscale is the blur; no filter pass is needed.
  This also *shrinks* the animated area on the widest, most expensive displays.

## Power

`index.html#calm` sets `--t:3`, and every duration in the file routes through
`calc(var(--t)*…)`, so one variable slows everything. Nothing in WebKit exposes
Low Power Mode, so this is the only lever the page has — pair it with Plash's own
deactivate-on-battery setting.
