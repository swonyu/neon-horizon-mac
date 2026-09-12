# The wallpaper scene

Edit the sources under `wallpaper/build/`, then use the [rebuild commands](../README.md#animated-wallpaper).
The HTML is generated; do not hand-edit `wallpaper/index.html`.

## Composition

The sunset and its reflection are the focal point. The foreground grade lowers
bright pavement while retaining the sky, so small traffic lights, boats and rain
impacts support that subject. The city and boat images are embedded WebPs, and
seeded SVG rain tiles keep the page self-contained and offline.

`.camera` defines the viewport; `.world` fits with small overscan and drifts; a masked near-plane copy
of the painting scales slowly to suggest depth. Boats bob independently, and
flipped reflections extend below their waterlines. The reflection transform
translates the sprite before applying the negative vertical scale; without that
translation, it renders upward into the hull.

Pavement smears fade toward all sides through a centered ellipse. Boat light
columns use a top-anchored ellipse, tapering sideways and down toward the water;
this avoids the previous rectangular edges without adding layers.

Animation periods vary to reduce obvious synchronization. Some are deliberately
coupled: the world drift and near-plane dolly both use 233 seconds. The falling
tile offsets alone recur after about 48.91 minutes; this is not the repeat period
of the entire rain field, whose gusts, squalls and storm have separate clocks.
There is no measured full-scene recurrence claim.

The irregular keyframes still use eased segments with zero endpoint velocity.
They are an aesthetic choice, not proof of continuous motion without dwell.
Lightning uses two offset events; both are not gated to the storm maximum.

## Measured image gates

`prepare_images.py` prints these checks and exits before saving outputs if a gate
fails. Values below use the script's 0–255 luma measurement on fixed image regions.

| Gate | Purpose |
|---|---|
| Promenade p95 between 120 and 130 | Keep bright pavement below the sunset |
| Promenade p05 no more than 5 | Retain dark foreground values |
| Sky mean changes by no more than 1 | Preserve the sky while grading the foreground |
| Sky p95 exceeds promenade p95 | Verify the intended brightness hierarchy |

The script decodes sRGB to linear RGB, converts to Oklab, adjusts lightness and
chroma together, then converts back. The separate preview bloom approximates the
visual treatment; it is not a captured browser frame. `still.png` is a
representative static painting for the ordinary wallpaper and Lock Screen.
It omits animated overlays and display-dependent cropping/filtering.

The checked reference environment is Python 3.12, NumPy 2.3.5, Pillow 12.3.0 and
libwebp 1.6.0. Assembly resets its random seed on each build, including repeat
calls in one process. All prepared assets must exist before assembly; complete
HTML is published atomically. Encoder upgrades may change compressed bytes.

## Accessibility and calm mode

System Reduce Motion disables animation, hides transient accents and leaves a
static composition. Elements need declared base values because `animation:none`
removes values supplied only by keyframes. Light and haze keep their declared
storm-scaled baseline; they must not become brighter than their normal range
merely because animation is disabled.

`index.html#calm` sets native animation playback rates to one third. Adding or
removing that fragment updates the speed without changing the current animation
position. The rate is reapplied when Reduce Motion changes recreate animations.
It changes speed,
not a measured frame-rate or energy limit. Use Plash's deactivate-on-battery
setting when you want the animation to stop on battery.

The page pauses CSS animations, including pseudo-elements, when the browser
reports it hidden. Hidden and Reduce Motion states also clear `will-change` hints. Another window covering the wallpaper does not necessarily
produce that signal. Plash behavior and system settings determine the remaining
lifecycle.

## Depth, crop and rendering cost

The near plane reuses the same encoded painting, but rendering it may allocate
additional surfaces. Its feathered mask blends along the parapet. The mask's
31.1-degree direction and 31.35% center follow from the two painted endpoints at
world coordinates (24%, 62%) and (66%, 100%) in a 3:2 world.

The world stays 3:2 and uses `width:min(102cqw,153cqh)` against the viewport.
This gives a continuous fit with 2% overscan and a blurred surround. Both boat
paths, waterfalls and painted puddle centers remain visible at the six checked
aspect ratios. The painting clips overlay overflow.

Weather now shares those painting coordinates. Rain tile size, travel and
overscan scale together; the near-rain mask stays still and transparent over
the sky. Shimmer moves a repeated stripe field beneath a stationary mask.

Thirty glints and fourteen river impacts use four conservative source-image
water regions with soft edges. This is a hand-tuned placement map, not general
water detection; changing the painting requires updating it. Eight facade
window anchors, two warm lamps and the cyan emitter follow inspected sources.

Bloom is rendered from a quarter-sized element and scaled up. That describes the
geometry, not a guaranteed GPU saving: filter surfaces, cache behavior, device
pixel ratio and compositing are browser-dependent. There is no measured 12%
motion-area budget, 3% accent-area bound or 1/16 GPU-cost guarantee. Frame time,
battery use and perceived smoothness require a rendered test on the target Mac.

## Regression checks

`tests/check.py` checks embedded assets, SVG gradient encoding, declared static
emitter opacity, rain speed fallbacks, storm blend structure, river-impact
placement, visibility pausing and calm transitions. Its interaction execution
uses a mocked document when Node.js is available.

`tests/build-selfcheck.py` checks reflection geometry, static atmosphere,
repeatable assembly, missing-asset and publication failures, and preservation of
previous outputs after a rejected grade, stationary shimmer, water-mask blending
and inactive animation hints. `water-selfcheck.py` checks emitted placement
bounds across 65 seeds; `framing-selfcheck.py` checks six aspect ratios, complete
boat paths, near-rain sky exclusion and seamless proportional rain tiles.
The grading check requires Pillow and
NumPy; the others use only the standard library. Lua checks cover the optional
controls separately. See the [audit record](AUDIT-2026-09-12.md) for what was
actually verified and which live checks remain. The subsequent
[wallpaper critique](WALLPAPER-CRITIQUE.md) records the focused visual-source pass.
