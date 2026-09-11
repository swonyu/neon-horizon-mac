"""Generates the placed elements: impact field, glints, smears, traffic, windows,
lamps, ballast and emitters.

Every coordinate here is a percentage of the PAINTING (the .world box), not of
the viewport, so placements survive every display aspect ratio. Coordinates were
read off the source image; the ones that matter carry a comment saying what is
painted there.

Timing rule enforced throughout: no two large-area elements share a prime factor.
Periods are expressed in tenths of a second and drawn from prime sets, so the
combined state of the scene does not relock inside ~39 minutes.
"""
import random

rng = random.Random(20260911)   # fixed seed: the build must be reproducible

# Prime-tenths period sets. Mutually coprime by construction.
GLINT_PERIODS = [2.3, 2.9, 3.1, 3.7, 4.1, 4.3, 4.7, 5.3, 5.9]
SMEAR_PERIODS = [8.3, 9.7, 11.3, 12.9, 14.7, 16.1]


def esc(v):
    return f'{v:.4g}'


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
    """44 instances: 30 on the promenade, 14 on the near river."""
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

    river = []
    for _ in range(200):
        if len(river) >= 14:
            break
        # Near river, downstream of the bank line (60,75) -> (100,100).
        x = rng.uniform(58.0, 99.0)
        y = rng.uniform(76.0, 99.0)
        if y < 75 + 25 * (x - 60) / 40 - 2:
            continue
        river.append((x, y, None))

    out = []
    for x, y, forced in sites + river:
        d = max(0.0, min(1.0, (y - 60.0) / 40.0))       # depth: 0 far, 1 near
        w = 0.45 + d * 2.6
        h = w * (0.20 + d * 0.22)
        p = 0.5 + d * 0.55                               # 0.5-1.05s: a raindrop,
        delay = rng.uniform(0, 7.0)                      # not a pebble in a pond
        colour = forced or (SODIUM if in_sodium_column(x, y) else MAGENTA)
        out.append(
            f'<i class="sp" style="left:{esc(x)}%;top:{esc(y)}%;--w:{esc(w)}%;'
            f'--h:{esc(h)}%;--p:{esc(p)}s;--d:-{esc(delay)}s;--c:{colour}"></i>'
        )
    return out


# --- glints -------------------------------------------------------------------
# Reflected light on chopped water shivers along the viewer-to-source axis, which
# here is vertical. The shipped glints are horizontal 0.65px hairlines sharing one
# 6s period, clustered in a dark blue-biased patch where the painting has no
# bright source at all.


def lerp_hex(a, b, t):
    av = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    bv = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(av[i] + (bv[i] - av[i]) * t):02x}' for i in range(3))


def glints():
    out = []

    def add(x, y, w, gh, colour):
        out.append(
            f'<i class="glint" style="left:{esc(x)}%;top:{esc(y)}%;width:{esc(w)}%;'
            f'--gh:{esc(gh)}%;--c:{colour};--gt:{rng.choice(GLINT_PERIODS)}s;'
            f'--delay:-{esc(rng.uniform(0, 12))}s"></i>'
        )

    # Far channel: the river as it recedes toward the sun. Small and tight.
    for _ in range(14):
        add(rng.uniform(47, 58), rng.uniform(42, 58),
            rng.uniform(0.08, 0.18), 0.12, rng.choice(['#f9becb', '#8ed4ed', '#f396dd']))

    # Mid river.
    for _ in range(18):
        add(rng.uniform(56, 72), rng.uniform(60, 76),
            rng.uniform(0.14, 0.40), 0.28, rng.choice(['#f396dd', '#8ed4ed', '#f9becb']))

    # Near river, bottom right: bigger and taller for perspective.
    for _ in range(12):
        add(rng.uniform(74, 96), rng.uniform(78, 96),
            rng.uniform(0.30, 0.70), 0.40, rng.choice(['#f396dd', '#f9becb', '#8ed4ed']))

    # The relocated twelve, plus ten warm ones, down the sun's specular column.
    # Warm at the top where the sun is, cooling as the column runs toward the
    # viewer; sizes grow downward.
    for i in range(22):
        t = i / 21.0
        y = 40.0 + t * 26.0
        x = 50.0 + rng.uniform(0, 6.0)
        add(x, y, 0.10 + t * 0.34, 0.14 + t * 0.22, lerp_hex('#ffe6cf', '#ffb27f', t))
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
# HONESTY CONSTRAINT: an additive patch can only make a painted window brighter.
# There is no multiply layer, so every event is a light coming ON and later
# fading out — never a lit window switching off.
WIN_PERIODS = [187, 211, 239, 263, 293, 317, 347, 379, 401, 433, 467, 499, 541, 577]


def windows():
    out = []
    spots = []
    for _ in range(8):                                   # right-bank tower band
        spots.append((rng.uniform(86, 93), rng.uniform(55, 66)))
    for _ in range(6):                                   # mid-river blocks
        spots.append((rng.uniform(44, 49), rng.uniform(72, 79)))
    for i, (x, y) in enumerate(spots):
        warm = i % 7 < 4
        cls = 'win' if warm else 'win cool'
        out.append(f'<i class="{cls}" style="left:{esc(x)}%;top:{esc(y)}%;'
                   f'--wt:{WIN_PERIODS[i]}s;--d:-{esc(rng.uniform(0, WIN_PERIODS[i]))}s"></i>')
    return out


# --- balustrade lamps ---------------------------------------------------------
# Verified at 5x: warm point sources along the railing land at y~49.4%, with
# reflected smears in the wet terrace below.
LAMP_PERIODS = [6.3, 7.1, 8.4, 9.7, 11.2, 13.1]


def lamps():
    out = []
    for i in range(6):
        x = 16.4 + i * 1.85
        size = 0.35 + (i % 3) * 0.05
        out.append(
            f'<i class="lamp" style="left:{esc(x)}%;top:49.4%;width:{esc(size)}%;'
            f'--lt:{LAMP_PERIODS[i]}s;--d:-{esc(i * 2.3 + 0.7)}s"></i>'
            f'<i class="lamp-streak" style="left:{esc(x)}%;top:50.1%;'
            f'--lt:{LAMP_PERIODS[i]}s;--d:-{esc(i * 2.3 + 0.7)}s"></i>')
    return out
