# Animated wallpaper implementation plan

Goal: resolve W01–W13 in the [critique](../WALLPAPER-CRITIQUE.md), preserving the
magenta painting, portable single HTML file and current native Mac setup.

Approach: refine the existing CSS/SVG scene. A continuous aspect-preserving fit
keeps the subjects visible; explicit painted-surface regions replace guessed
placement bands. Native animation-rate control handles calm changes without a
new render loop. No runtime dependency or raster-art change is needed.

- [x] Inspect source images and every animated component; classify proven
  geometry/behavior failures separately from unverified visual preferences.
- [x] W01/W02: in `wallpaper/build/scene.py`, center the world with
  `width:min(102cqw,153cqh)`, a 3:2 ratio, small drift around the center and
  clipped effect overflow. Check continuity and subject bounds at 9:16, 3:2,
  16:10, 16:9, 21:9 and 32:9.
- [x] W03/W04/W05: in `scatter.py`, define conservative water rectangles from
  the source painting, sample inside their animated margins, and emit a soft
  SVG water mask. In `build.py`/`scene.py`, mask water lights together and move
  the solar column below the bridges. Check complete effect extents, original
  erroneous positions, finite values, counts and deterministic assembly.
- [x] W06/W07/W13: keep the shimmer mask stationary and animate its stripe
  pseudo-element; align the weather and near-rain exclusion to the painting.
  Scale rain tiles and travel with the painting. Check pattern period, overscan,
  mask bounds and sky exclusion.
- [x] W08/W09: update playback rates while preserving animation times; reapply
  the rate after reduced-motion changes and clear preparation hints while
  hidden/static. Exercise the actual generated script against mocked native
  animation objects, including visible/hidden and calm/ordinary transitions.
- [x] W10/W11/W12: replace random windows and lamp grids with inspected points;
  align the cyan emitter. Check generated coordinates and the centered-window
  convention against the source anchors.
- [x] Update existing regression expectations, run the full portable suite
  with image dependencies and independent diff review, rebuild the final HTML,
  and document remaining rendered-review limits.
Delivery: commit locally, integrate into matching main while preserving unrelated
edits, validate a ZIP from the commit, and append the actual work to the session
note. The receipt beside the archive records the completed delivery and exact hashes.

Ownership: root edits the scene, builder, existing checks and documentation.
The placement worker owns `scatter.py` and its dedicated geometry check only.
All browser restrictions and the user's local-only publication preference remain
in effect. Passing source checks do not certify a live Plash installation.
