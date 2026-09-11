"""W0 steps 2-3: regenerate the rain tiles.

Three defects in the shipped tiles are fixed here.

1. PLACEMENT. Uniform random placement clumps, and clumps are what the eye
   locks onto as a repeating constellation. Poisson-disc (blue-noise) placement
   keeps drops apart so no shape forms.
2. SEAMS. A drop near the tile edge was clipped, so the tile announced its own
   boundary. Every drop that crosses an edge is now emitted again on the far
   side, wrapped.
3. MOTION BLUR. A rain streak is a smear, not a hairline. Each drop is drawn as
   three concentric rects sharing a centre line, at widths 1.2/2.4/3.6 and
   falling opacities, which bakes a soft horizontal falloff into the tile. This
   is why .rain.near must NOT carry filter:blur() — a filter on a subtree whose
   child translates every frame re-applies forever, on battery.
"""
import random
from urllib.parse import quote

# name -> (size, count, width range, height range, gradient stops)
COOL = ('#bcb7df', '#d2e8f4', '#f1ecff')
# Pale warm lilac sampled from the sunset sky: at layer opacity .21 the cool
# stops put a visible cyan cast over the magenta sky. These bring it near-neutral.
LILAC = ('#cfc3e0', '#e3d7ec', '#f4ecff')
# Lamp throw. Produced as its own tile, never as a filter on a cool one.
WARM = ('#6b4a2a', '#ffc98a', '#ffe2b8')

TILES = {
    'far':  dict(size=768,  count=90,  w=(0.45, 0.75), h=(6.0, 13.0), stops=LILAC, blur=False),
    'mid':  dict(size=1536, count=120, w=(0.66, 1.12), h=(15.0, 26.0), stops=COOL, blur=True),
    'near': dict(size=1536, count=100, w=(1.10, 1.50), h=(29.0, 42.0), stops=COOL, blur=True),
    'warm': dict(size=1536, count=100, w=(1.10, 1.50), h=(29.0, 42.0), stops=WARM, blur=True),
}

# Relative widths and opacity multipliers of the three-rect motion-blur stack.
BLUR_STACK = ((1.0, 0.55), (2.0, 0.25), (3.0, 0.12))


def poisson_points(rng, size, count, min_dist):
    """Bridson-style dart throwing on a torus, so distances wrap with the tile."""
    pts = []
    tries = 0
    limit = count * 400
    while len(pts) < count and tries < limit:
        tries += 1
        p = (rng.uniform(0, size), rng.uniform(0, size))
        ok = True
        for q in pts:
            dx = abs(p[0] - q[0])
            dy = abs(p[1] - q[1])
            dx = min(dx, size - dx)          # torus distance: the tile repeats,
            dy = min(dy, size - dy)          # so edge-adjacent drops are neighbours
            if dx * dx + dy * dy < min_dist * min_dist:
                ok = False
                break
        if ok:
            pts.append(p)
    return pts


def rects_for_drop(x, y, w, h, opacity, size, blur):
    """Emit the rects for one drop, wrapped across both tile edges."""
    stack = BLUR_STACK if blur else ((1.0, 1.0),)
    out = []
    for wm, om in stack:
        width = w * wm
        alpha = opacity * om
        if alpha < 0.012:
            continue
        left = x - width / 2
        # Wrap: a drop crossing an edge is drawn again on the opposite side.
        xs = [left]
        if left < 0:
            xs.append(left + size)
        elif left + width > size:
            xs.append(left - size)
        ys = [y]
        if y < 0:
            ys.append(y + size)
        elif y + h > size:
            ys.append(y - size)
        for xv in xs:
            for yv in ys:
                # Coordinates are one decimal and fill/rx live on the parent <g>:
                # the tile is percent-encoded into the stylesheet, where every
                # character costs ~3 bytes, so precision that cannot be seen at
                # 1px wide is pure payload.
                out.append(
                    f'<rect x="{xv:.1f}" y="{yv:.1f}" width="{width:.2f}" '
                    f'height="{h:.1f}" opacity="{alpha:.2f}"/>'
                )
    return out


def build_tile(name, seed):
    spec = TILES[name]
    size = spec['size']
    rng = random.Random(seed)
    # Spacing chosen so dart throwing reliably reaches `count` without thinning.
    min_dist = size / (spec['count'] ** 0.5) * 0.62
    pts = poisson_points(rng, size, spec['count'], min_dist)

    body = []
    for x, y in pts:
        w = rng.uniform(*spec['w'])
        h = rng.uniform(*spec['h'])
        opacity = rng.uniform(0.30, 0.98)
        body += rects_for_drop(x, y, w, h, opacity, size, spec['blur'])

    a, b, c = spec['stops']
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}">'
        f'<defs><linearGradient id="r" x2="0" y2="1">'
        f'<stop stop-color="{a}" stop-opacity="0"/>'
        f'<stop offset=".8" stop-color="{b}" stop-opacity=".8"/>'
        f'<stop offset="1" stop-color="{c}" stop-opacity=".3"/>'
        # `fill` is an inherited property so it lives on the <g>, but `rx` is a
        # geometry property and does NOT inherit — it has to come through CSS or
        # every drop renders square-cornered.
        f'</linearGradient><style>rect{{rx:.45px}}</style></defs>'
        # '#' is written literally here: quote() below percent-encodes it to
        # %23 exactly once. Pre-encoding it produces %2523, a dangling
        # paint-server reference, and every drop renders with no fill.
        f'<g fill="url(#r)">'
        + ''.join(body) +
        '</g></svg>'
    )
    return svg, len(pts), len(body)


def data_uri(svg):
    # Match the shipped file's encoding: percent-encoded SVG, not base64.
    # '#' must survive as %23 (already written that way in the fill refs).
    return 'url("data:image/svg+xml,' + quote(svg, safe='') + '")'


def build_all():
    seeds = {'far': 20260911, 'mid': 20260912, 'near': 20260913, 'warm': 20260914}
    out = {}
    for name in TILES:
        svg, drops, rects = build_tile(name, seeds[name])
        out[name] = data_uri(svg)
        yield name, drops, rects, len(out[name])


if __name__ == '__main__':
    for name, drops, rects, uri_len in build_all():
        print(f'{name:<5} {drops:4d} drops -> {rects:5d} rects, uri {uri_len/1024:6.1f} KB')
