"""Generates the placed elements: impact field, glints, smears, traffic, windows,
lamps, ballast and emitters.

Emitted coordinates are percentages of the PAINTING (the .world box), not the
viewport. Inspected water regions and light anchors retain their source-pixel
coordinates below and convert to percentages when emitted.

Different periods and phases vary the local accents. Some periods share factors
or are reused; this generator does not establish a scene-wide repeat interval.
"""
import random

rng = random.Random(20260911)   # build.main resets this seed for each assembly

# Varied accent periods, in seconds.
GLINT_PERIODS = [2.3, 2.9, 3.1, 3.7, 4.1, 4.3, 4.7, 5.3, 5.9]
SMEAR_PERIODS = [8.3, 9.7, 11.3, 12.9, 14.7, 16.1]

# Clear-water cores inspected in the 1536x1024 source painting. These deliberately
# exclude bridge decks, tower silhouettes and the foreground parapet.
WATER_REGIONS = ((815, 505, 830, 536), (821, 576, 838, 617),
                 (895, 710, 958, 750), (1315, 890, 1470, 955))


def esc(v):
    return f'{v:.4g}'


def water_mask():
    """Soft water-only light mask in source-image coordinates; encode at assembly."""
    rectangles = ''.join(
        f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" '
        'fill="url(#water-x)" mask="url(#fade-y)"/>'
        for x0, y0, x1, y1 in WATER_REGIONS)
    stops = ('<stop offset="0%" stop-color="#fff" stop-opacity="0"/>'
             '<stop offset="5%" stop-color="#fff"/>'
             '<stop offset="95%" stop-color="#fff"/>'
             '<stop offset="100%" stop-color="#fff" stop-opacity="0"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="1536" height="1024" '
            'viewBox="0 0 1536 1024"><defs>'
            '<linearGradient id="water-x" x1="0%" y1="0%" x2="100%" y2="0%">' + stops +
            '</linearGradient><linearGradient id="water-y" x1="0%" y1="0%" x2="0%" y2="100%">' + stops +
            '</linearGradient><mask id="fade-y" maskUnits="objectBoundingBox" '
            'maskContentUnits="objectBoundingBox" x="0" y="0" width="1" height="1">'
            '<rect width="1" height="1" fill="url(#water-y)"/>'
            '</mask></defs>' + rectangles + '</svg>')


# --- impact field -------------------------------------------------------------
# The promenade is the largest area of the frame and the closest to the viewer,
# and today it receives two elliptical puddles totalling 1.3% of the frame. Rain
# has to land on all of it.

SODIUM = '#ffb27a'      # the lamp's reflection column, x 30-35% / y 76.4-83.4%
MAGENTA = '#ff9ad8'     # measured tint of both painted puddles: G far below R and B
WARM_STONE = '#e8c9a8'

# Painted puddles stay as density peaks: the painter already put standing water
# there, so impacts land where water is.
PEAKS = [(19.3, 83.0), (27.0, 95.0)]
# Verified extra pavement sites.
EXTRA = [(10, 70, WARM_STONE), (17, 76, MAGENTA), (8, 84, WARM_STONE),
         (22, 88, MAGENTA), (14, 95, MAGENTA), (29, 97, WARM_STONE)]


def in_sodium_column(x, y):
    return 30 <= x <= 35 and 76.4 <= y <= 83.4


def impact_field():
    """36 impacts on the promenade.

    These are emitted inside .plane-near so they ride the dollying promenade
    instead of drifting off their painted ground. The river impacts must NOT go
    here: .plane-near's mask goes transparent on the river side of the parapet,
    which is exactly where they land, so it would multiply them by zero.
    """
    sites = []

    # Promenade quad, in world percent. Bounded by the parapet on the right.
    for _ in range(300):
        if len(sites) >= 24:
            break
        x = rng.uniform(3.0, 34.0)
        y = rng.uniform(62.0, 99.0)
        # The parapet runs roughly (20,62) -> (48,100); stay left of it.
        if x > 20 + 28 * (y - 62) / 38 + 6:
            continue
        # 2x weight along the base of the parapet, where run-off pools.
        near_parapet = abs(x - (20 + 28 * (y - 62) / 38)) < 5
        if not near_parapet and rng.random() < 0.35:
            continue
        sites.append((x, y, None))

    for px, py in PEAKS:                    # density peaks on the painted puddles
        for _ in range(3):
            sites.append((px + rng.uniform(-3.2, 3.2), py + rng.uniform(-1.4, 1.4), None))
    for x, y, c in EXTRA:
        sites.append((float(x), float(y), c))

    return _emit(sites)


def river_impacts():
    """14 complete rings on clear water, outside the promenade's moving mask."""
    river = []
    for (x0, y0, x1, y1), count in zip(WATER_REGIONS[2:], (6, 8)):
        # The mask is fully opaque only beyond each region's 5% edge fade.
        sx, sy = (x1 - x0) * .05, (y1 - y0) * .05
        x0, y0, x1, y1 = x0 + sx, y0 + sy, x1 - sx, y1 - sy
        # The deepest point gives the largest ring; reserve its full radius,
        # another 4 source pixels for nominal blur/spread and rounding. The mask
        # can still trim very faint Gaussian tails beyond that nominal footprint.
        w, h, _ = _impact_dimensions(y1 / 10.24)
        dx, dy = w * 15.36 / 2 + 4, h * 10.24 / 2 + 4
        for _ in range(count):
            x = rng.uniform(x0 + dx, x1 - dx) / 15.36
            y = rng.uniform(y0 + dy, y1 - dy) / 10.24
            river.append((x, y, None))
    return _emit(river)


def _impact_dimensions(y):
    d = max(0.0, min(1.0, (y - 60.0) / 40.0))  # depth: 0 far, 1 near
    w = 0.45 + d * 2.6
    return w, w * (0.20 + d * 0.22), 0.5 + d * 0.55


def _emit(sites):
    out = []
    for x, y, forced in sites:
        w, h, p = _impact_dimensions(y)
        delay = rng.uniform(0, 7.0)
        colour = forced or (SODIUM if in_sodium_column(x, y) else MAGENTA)
        out.append(
            f'<i class="sp" style="left:{esc(x)}%;top:{esc(y)}%;--w:{esc(w)}%;'
            f'--h:{esc(h)}%;--p:{esc(p)}s;--d:-{esc(delay)}s;--c:{colour}"></i>'
        )
    return out


# --- glints -------------------------------------------------------------------
# Small, warm glints follow the distant solar reflection; larger magenta/cool
# glints occupy clear middle and near water. Every full animated box stays wet.


def glints():
    out = []
    layout = ((6, .08, .14, .12), (6, .10, .18, .16),
              (8, .16, .32, .28), (10, .30, .55, .40))
    for index, ((x0, y0, x1, y1), (count, low, high, gh)) in enumerate(zip(WATER_REGIONS, layout)):
        sx, sy = (x1 - x0) * .05, (y1 - y0) * .05
        x0, y0, x1, y1 = x0 + sx, y0 + sy, x1 - sx, y1 - sy
        colours = ('#ffe6cf', '#ffb27f', '#f9becb') if index < 2 else ('#f396dd', '#8ed4ed', '#f9becb')
        for _ in range(count):
            w = rng.uniform(low, high)
            # scaleY(1.5) grows .25 heights above top and 1.25 below top.
            # A .2px inset also covers four-significant-digit serialization.
            x = rng.uniform(x0 + .2, x1 - w * 15.36 - .2) / 15.36
            y = rng.uniform(y0 + .25 * gh * 10.24 + .2,
                            y1 - 1.25 * gh * 10.24 - .2) / 10.24
            out.append(
                f'<i class="glint" style="left:{esc(x)}%;top:{esc(y)}%;width:{esc(w)}%;'
                f'--gh:{esc(gh)}%;--c:{rng.choice(colours)};--gt:{rng.choice(GLINT_PERIODS)}s;'
                f'--delay:-{esc(rng.uniform(0, 12))}s"></i>')
    return out


# --- promenade smears ---------------------------------------------------------
# Anchored on actual painted reflection columns. Four warm, two magenta: the
# painting carries both, and an all-orange set looks wrong.
SMEARS = [(7.4, 84, 9, '#ffb86a'), (11.6, 70, 7, '#ffb86a'), (19.8, 88, 11, '#e879c8'),
          (26.5, 79, 8, '#ffb86a'), (31.1, 83, 10, '#ffb86a'), (30.2, 92, 7, '#e879c8')]


def smears():
    return [
        f'<i class="smear" style="left:{esc(x)}%;top:{esc(y)}%;height:{esc(h)}%;'
        f'--c:{c};--st:{SMEAR_PERIODS[i]}s;--d:-{esc(i * 3.7 + 1.3)}s"></i>'
        for i, (x, y, h, c) in enumerate(SMEARS)
    ]


# --- traffic ------------------------------------------------------------------
# Every lane is a deck the painter already drew. A moving light on a road reads as
# "inhabited city" more reliably than any invented element.
# name, left, top, width, rotation, period, cars, reverse, kind, mask
LANES = [
    # Viaduct. The painter already put a lit stationary car at fx 24.4-27.8%, so
    # these are headlight DOTS, not car-length bars, or the painted one reads as
    # a duplicate ghost.
    dict(n='L1', left=13.6, top=25.45, w=23.7, rot=-5.8, t=26, cars=3, rev=False,
         size=3.0, mask=None),
    # The arch span SAGS to fy 43% at mid-span — ~17px below the chord — so it is
    # two lanes, not one, split at fx 51.5%.
    dict(n='L2a', left=35.0, top=40.05, w=16.6, rot=6.0, t=30, cars=2, rev=False,
         size=6.0, mask=None),
    dict(n='L2b', left=51.5, top=42.65, w=18.5, rot=-1.65, t=34, cars=2, rev=True,
         size=6.0, mask=None),
    # The causeway passes BEHIND two foreground spire clusters; the mask punches
    # them out so cars fade behind the towers and re-emerge.
    dict(n='L3', left=52.0, top=59.65, w=50.6, rot=18.3, t=21, cars=4, rev=False,
         size=6.0,
         mask='linear-gradient(90deg,transparent 0,#000 6%,#000 26%,transparent 29%,'
              'transparent 38%,#000 41%,#000 47%,transparent 50%,transparent 57%,'
              '#000 60%,#000 92%,transparent 100%)'),
    dict(n='L4', left=86.7, top=55.15, w=13.3, rot=0.3, t=40, cars=2, rev=True,
         size=6.0, mask=None),
]
AIR = [
    dict(n='A1', left=62.0, top=27.95, w=36.0, t=78, cars=3, rev=False, op=0.55),
    dict(n='A2', left=58.0, top=14.85, w=42.0, t=62, cars=3, rev=True, op=0.70),
]

EDGE_FADE = 'linear-gradient(90deg,transparent,#000 7%,#000 90%,transparent)'


def travel(size_pct):
    """A car is `size` percent of its lane and starts at left:-size. Percent
    translate resolves against the CAR's box, so carrying it 100%+size of the
    lane means translating 100*(100+size)/size of itself."""
    return 100.0 * (100.0 + size_pct) / size_pct


def traffic():
    out = []
    for L in LANES:
        mask = L['mask'] or EDGE_FADE
        style = (f'left:{esc(L["left"])}%;top:calc({esc(L["top"])}% - .35%);'
                 f'width:{esc(L["w"])}%;transform:rotate({esc(L["rot"])}deg);'
                 f'--ct:{L["t"]}s;--tv:{esc(travel(L["size"]))}%;'
                 f'-webkit-mask-image:{mask};mask-image:{mask}')
        cars = []
        for i in range(L['cars']):
            delay = -L['t'] * i / L['cars'] - rng.uniform(0, 1.5)
            cls = 'car tail' if L['rev'] else 'car'
            cars.append(f'<i class="{cls}" style="width:{esc(L["size"])}%;'
                        f'left:-{esc(L["size"])}%;--d:{esc(delay)}s"></i>')
        out.append(f'<div class="lane" style="{style}">' + ''.join(cars) + '</div>')

    for A in AIR:
        style = (f'left:{esc(A["left"])}%;top:calc({esc(A["top"])}% - .35%);'
                 f'width:{esc(A["w"])}%;--ct:{A["t"]}s;--tv:{esc(travel(7.0))}%;'
                 f'-webkit-mask-image:{EDGE_FADE};mask-image:{EDGE_FADE}')
        craft = []
        for i in range(A['cars']):
            delay = -A['t'] * i / A['cars'] - rng.uniform(0, 3.0)
            rev = ' rev' if A['rev'] else ''
            craft.append(
                f'<b class="flyer{rev}" style="width:7%;left:-7%;--d:{esc(delay)}s">'
                f'<i style="opacity:{esc(A["op"])}"></i></b>')
        out.append(f'<div class="lane air" style="{style}">' + ''.join(craft) + '</div>')
    return out


# --- windows ------------------------------------------------------------------
# Small patches suggest windows coming on, then fading away. Normal alpha
# blending is not additive and can change the painted color under each patch.
WIN_PERIODS = [187, 211, 239, 263, 293, 317, 347, 379]
# Painted window centers in source pixels: two central facades, one right tower,
# and the left distant tower. CSS centers each small patch on its light.
WINDOW_ANCHORS = ((728, 726), (728, 746), (796, 692), (796, 700),
                  (793, 706), (1300, 591), (648, 483), (651, 496))


def windows():
    out = []
    for i, (px, py) in enumerate(WINDOW_ANCHORS):
        x, y = px / 15.36, py / 10.24
        cls = 'win' if i < 5 else 'win cool'
        out.append(f'<i class="{cls}" style="left:{esc(x)}%;top:{esc(y)}%;'
                   f'--wt:{WIN_PERIODS[i]}s;--d:-{esc(rng.uniform(0, WIN_PERIODS[i]))}s"></i>')
    return out


# --- balustrade lamps ---------------------------------------------------------
# Two inspected warm railing lights, each with its actual source-pixel height.
LAMP_PERIODS = [6.3, 7.1]
LAMP_ANCHORS = ((232, 501), (331, 505))


def lamps():
    out = []
    for i, (px, py) in enumerate(LAMP_ANCHORS):
        x, y = px / 15.36, py / 10.24
        size = 0.35 + i * 0.05
        out.append(
            f'<i class="lamp" style="left:{esc(x)}%;top:{esc(y)}%;width:{esc(size)}%;'
            f'--lt:{LAMP_PERIODS[i]}s;--d:-{esc(i * 2.3 + 0.7)}s"></i>'
            f'<i class="lamp-streak" style="left:{esc(x)}%;top:{esc(y + .7)}%;'
            f'--lt:{LAMP_PERIODS[i]}s;--d:-{esc(i * 2.3 + 0.7)}s"></i>')
    return out
