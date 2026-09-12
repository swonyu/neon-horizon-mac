# Animated wallpaper critique — 12 September 2026

Reviewed the complete animation at `7f833a6`: its painting and boat assets,
generated scene, placement data, rain tiles, timing, display framing,
accessibility, lifecycle, build and existing checks. Three independent source
reviews covered movement, framing and painted-surface alignment.

The painting has a strong magenta sunset, readable architectural depth and warm
foreground contrast. It does not need replacement. Its weakest area is how the
added effects relate to that painting: random rectangles put water glints and
window lights on the wrong surfaces, and screen-relative cropping and rain masks
do not consistently preserve the same composition.

This is a source-and-image review. The user opened the correct local wallpaper
in Chrome and the tab inventory confirmed it. The browser tool still rejected
selecting that tab for inspection and explicitly prohibited alternate routes.
A subsequent user-supplied recording was reviewed as described below. It shows an
older loaded scene, so it does not verify the current build or provide measured
frame-time or power results.

## Findings

| ID | Finding and evidence | Resolution | Status |
|---|---|---|---|
| W01 | The wide-display breakpoint shrinks the world by 18.9% at viewport ratio about 1.829. | Use one continuous fit rule with small overscan; center the painting over its existing blurred backdrop. | Fixed; checked in source |
| W02 | At 9:16, the visible source spans only x32.2–68.24%; boats, waterfalls and most pavement disappear. | Fit both image dimensions so narrow previews retain the subjects. Clip effects at the painting boundary. | Fixed; checked in source |
| W03 | River impacts include the promenade at (58.48%,95.51%) and towers around (66.44%,93.22%). | Sample conservative, image-verified water regions and keep complete ring extents inside them. | Fixed; checked in source |
| W04 | Glints appear on towers at (67.02%,69.86%), (67.46%,61.53%), and the central tower around (50.42%,64.76%). | Place fewer glints inside verified water regions, retaining depth-scaled sizes and varied phases. | Fixed; checked in source |
| W05 | The solar band starts at y31% and glitter at y38.56%, above visible water. | Re-anchor the solar effect to the actual reflection column and mask it to clear water between structures. | Fixed; checked in source |
| W06 | The 3.4px stripe loop moves its radial mask too, so that mask resets every 1.9/2.9 seconds. | Keep the mask stationary and translate a repeated stripe pseudo-element underneath it. | Fixed; checked in source |
| W07 | The near-rain mask is viewport-relative: its calculated opacity at the painted sun is about 0.21 at 3:2 and 0.23 on ultrawide framing. | Put weather in painting coordinates and use a stationary near-rain region that excludes the sky. | Fixed; checked in source |
| W08 | Changing CSS animation duration for calm mode changes phase at an existing elapsed time. | Change playback rate through the native Web Animations API, which preserves the current position. Resynchronize when reduced-motion preferences recreate animations. | Fixed; checked in source |
| W09 | Around 113 explicit animation-preparation hints remain when animation is hidden or disabled. | Clear `will-change` hints in hidden and Reduce Motion states. No energy-saving percentage is claimed. | Fixed; checked in source |
| W10 | Random window patches land on the parapet at (45.30%,78.15%), its cap at (47.21%,76.18%), and a bridge at (88.71%,56.54%). | Use eight individually inspected facade anchors and center patches on them. | Fixed; checked in source |
| W11 | The blue tower emitter is at (88.9%,60%), away from the cyan strip near (75.74%,38.02%). | Move and narrow the emitter around the actual source. | Fixed; checked in source |
| W12 | The evenly spaced lamp grid extends past the warm railing fixtures; its sixth point is on a cool background building. | Keep the two individually confirmed warm fixtures, each with its own vertical coordinate. | Fixed; checked in source |
| W13 | Rain tiles keep fixed pixel dimensions while the painting shrinks, making drops relatively larger and sparser in narrow previews. | Scale tile size, loop travel and overscan together in painting coordinates. | Fixed; checked in source |
| W14 | In the supplied recording, several pavement smears and boat glows have straight, rectangular sides. Their vertical-only gradient definitions remain unchanged in the newer source. | Use elliptical opacity falloff for these two existing light layers, retaining their placement, tint and motion. | Fixed in source; post-change footage pending |

## What was retained, and why

- **Painting and color:** retain the source image, grade and palette. Existing
  measured gates protect the sunset/pavement hierarchy. The base is 1536 × 1024;
  display scaling does not create native 4K detail.
- **Boats:** both travel over the near river. Their small bob and alternating
  drift fit the request for gentle movement. The long light columns can meet
  the image boundary; clipping keeps them off the blurred surround.
- **Rain:** seeded placement, edge wrapping and baked soft streaks are sound.
  Keep distinct depth layers and gust phases. Repeated impact locations and
  relative rain speed remain visual tuning questions, not demonstrated bugs.
- **Camera and depth:** retain the subtle drift and feathered foreground plane.
  Some segments ease to zero velocity; that is an aesthetic choice. Unviewed
  timing changes would not establish an improvement.
- **Waterfalls and mist:** their repeating textures and fades have valid loop
  geometry. Preserve their placements and restrained opacity.
- **Traffic:** preserve the deck paths, occlusion masks and aerial lanes. Their
  source-relative placement and wrapping need no new framework.
- **Atmosphere and lightning:** retain low-frequency weather and reduced-motion
  suppression. No flash-compliance claim can be made without rendered luminance
  and area measurements.
- **Performance:** keep CSS/SVG and embedded assets. Avoid adding a continuous
  JavaScript render loop, dependencies, networking or permanent controls over
  the painting. Layer dimensions and hint counts are not GPU measurements.
- **Packaging:** rebuild HTML from source, verify the exact package, and retain
  local-only publication. The existing host is outside this visual change.

## User-supplied recording review

Reviewed nine sampled frames from the first 30 seconds of a 48.015-second,
3022 × 1812 recording supplied on 12 September. The user identified the city
as the wallpaper open in Chrome. Later unrelated desktop content was excluded
from the wallpaper review and is not included in the package.

The recording contains the older pair of cool window squares on the foreground
parapet. Their positions match the old `(45.30%,78.15%)` and `(45.24%,77.36%)`
anchors; neither exists in the revised source. The enlarged, bottom-aligned
composition also agrees with the earlier framing. The separate Chrome tab inventory lists the current repository wallpaper path,
which is consistent with a tab that retained the older document after the file
changed. The footage itself does not show the URL or an exact build identifier.

Both boats visibly move over open water in the sampled interval and their
light columns extend below them. The painting retains its magenta sunset and
warm foreground. No additional boat-over-building defect or definite rain-loop
seam was established. Sampling a recording does not certify continuous smoothness,
the complete animation cycle, frame rate or battery use.

One new polish finding applies to code shared by both versions: pavement smears
and boat glows have straight lateral edges. W14 changes their opacity falloff to
ellipses, which reach transparency at both sides, using the existing backgrounds.
It adds no overlay elements, animation clocks or dependencies. The updated
appearance still needs a recording made after reloading the current file.

## Verification and limits

The first 13 source findings have corresponding repairs and runnable checks. The
[implementation plan](plans/2026-09-12-wallpaper-review.md) maps each repair to
its validation. The image rebuild passed the original brightness gates, and all
three embedded WebPs plus `still.png` remain byte-identical to the baseline.

The full portable Python suite passed with the reference image libraries. This
includes geometry across six aspect ratios, emitted water footprints across
65 seeds, shimmer period matching, deterministic assembly and failure recovery.
Node executed the generated script against mocked DOM and animation objects;
it checked visibility changes, native rate calls without resetting current
times, and reapplication after animation recreation. Native adapter testing used
a disposable preference domain; it did not apply the preset to personal settings.

Independent review caught a mismatch between the first soft mask's elliptical
core and rectangular placement bounds. The final mask uses a rectangular opaque
core containing every accepted footprint. River strokes scale with the painting;
the mask clips their soft outer tails to water. This corrects the source geometry
without asserting that simulated bounds measure perceived visibility.

The deliverable is a local repository and an archive of the final commit. No
push, wallpaper service installation or live Plash selection is part of this
pass. The verification receipt beside the ZIP records its exact commit, hashes
and package checks. Chrome's local-file inspection remains blocked; frame time,
power use, visual smoothness and the active desktop still require rendered
verification.

References: [Web Animations playback-rate updates](https://www.w3.org/TR/web-animations-1/#dom-animation-updateplaybackrate)
preserve animation position; [CSS will-change guidance](https://www.w3.org/TR/css-will-change/#will-change)
recommends dropping preparation hints when changes stop. These support the
implementation choices, not a performance or visual-quality certification.
