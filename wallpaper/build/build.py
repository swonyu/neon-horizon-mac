#!/usr/bin/env python3
"""Assembles wallpaper/index.html from the prepared assets and the scene template.

Run prepare_images.py first (it bakes the value knockdown and writes the WebP
assets); this script embeds them and emits the finished single-file wallpaper.

    python3 build/prepare_images.py
    python3 build/build.py
"""
import base64
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import rain_tiles          # noqa: E402
import scatter             # noqa: E402
import scene               # noqa: E402

OUT = HERE / 'out'
TARGET = HERE.parent / 'index.html'

# Two boats placed over the near river, with different bob periods.
BOATS = [
    dict(left=86.0026, top=93.5547, width=4.2, sail=160, bob=7.1, phase=-23),
    dict(left=93.0990, top=95.5000, width=3.2, sail=160, bob=8.3, phase=-15),
]

# Anchored on real painted sources. No swing exceeds .18.
EMITTERS = [
    dict(x=52.4, y=28.0, w=15, h=10, c='#ffc9a8', t=31.7, lo=.28, hi=.42, d=-11),   # sun
    dict(x=32.9, y=30.0, w=7, h=36, c='#ff2ea8', t=17.4, lo=.20, hi=.34, d=-29),    # neon column
    dict(x=32.2, y=70.5, w=4, h=3, c='#ffa04e', t=11.9, lo=.18, hi=.32, d=-7),      # promenade lamp
    dict(x=75.74, y=38.02, w=3.2, h=18, c='#3fc9ff', t=23.1, lo=.18, hi=.30, d=-19), # cyan facade strip
]

# Different periods and phases reduce regular coincidence between signs.
BALLAST = [
    dict(x=82.8, y=65.0, w=3.4, h=13.0, c='#e0409a', t=53, d=0),
    dict(x=82.4, y=53.5, w=2.4, h=2.6, c='#ff5ff0', t=71, d=-24),
    dict(x=34.5, y=44.0, w=2.2, h=9.0, c='#ff3df2', t=37, d=-11),
]


def data_uri(path, mime='image/webp'):
    return f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode('ascii')


def boats():
    out = []
    for b in BOATS:
        out.append(
            f'<div class="boat-anchor" style="left:{b["left"]:.4f}%;top:{b["top"]:.4f}%;'
            f'width:{b["width"]}%">'
            f'<div class="boat-drift" style="--sail-time:{b["sail"]}s;'
            f'--bob-time:{b["bob"]}s;--phase:{b["phase"]}s">'
            f'<div class="boat-bob">'
            f'<div class="boat-reflection"></div>'
            f'<div class="boat-glow"></div>'
            f'<div class="boat-art"></div>'
            f'</div></div></div>')
    return out


def emitters():
    return [
        f'<i class="emit" style="left:{e["x"]}%;top:{e["y"]}%;width:{e["w"]}%;'
        f'height:{e["h"]}%;--c:{e["c"]};--et:{e["t"]}s;--lo:{e["lo"]};--hi:{e["hi"]};'
        f'--d:{e["d"]}s"></i>'
        for e in EMITTERS
    ]


def ballast():
    return [
        f'<i class="ballast" style="left:{b["x"]}%;top:{b["y"]}%;width:{b["w"]}%;'
        f'height:{b["h"]}%;--c:{b["c"]};--bt:{b["t"]}s;--d:{b["d"]}s"></i>'
        for b in BALLAST
    ]


def main():
    required = [OUT / name for name in ('city.webp', 'boat.webp', 'city-blur.webp')]
    required.append(HERE / 'falltile.txt')
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        print('Missing build assets: ' + ', '.join(missing), file=sys.stderr)
        print('Run prepare_images.py for WebP assets; restore falltile.txt if missing.', file=sys.stderr)
        return 1

    tiles = {name: uri for name, uri, *_ in
             ((n, rain_tiles.data_uri(rain_tiles.build_tile(n, s)[0]))
              for n, s in (('far', 20260911), ('mid', 20260912),
                           ('near', 20260913), ('warm', 20260914)))}
    # The url("...") wrapper belongs to the CSS template, not the value.
    for k, v in tiles.items():
        tiles[k] = v[len('url("'):-len('")')]

    css = scene.CSS.substitute(
        CITY=data_uri(OUT / 'city.webp'),
        BOAT=data_uri(OUT / 'boat.webp'),
        CITYBLUR=data_uri(OUT / 'city-blur.webp'),
        WATERMASK='data:image/svg+xml,' + quote(scatter.water_mask(), safe=''),
        FALLTILE=(HERE / 'falltile.txt').read_text().strip(),
        RAIN_FAR=tiles['far'], RAIN_MID=tiles['mid'],
        RAIN_NEAR=tiles['near'], RAIN_WARM=tiles['warm'],
    )

    scatter.rng.seed(20260911)
    parts = {
        'IMPACT': scatter.impact_field(),
        'RIVER': scatter.river_impacts(),
        'SMEARS': scatter.smears(),
        'GLINTS': scatter.glints(),
        'BOATS': boats(),
        'TRAFFIC': scatter.traffic(),
        'LAMPS': scatter.lamps(),
        'BALLAST': ballast(),
        'WINDOWS': scatter.windows(),
        'EMITTERS': emitters(),
    }
    html = scene.DOC.substitute(CSS=css, **{k: ''.join(v) for k, v in parts.items()})
    descriptor, temporary = tempfile.mkstemp(dir=TARGET.parent, prefix='.wallpaper-', suffix='.html')
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write(html)
        os.replace(temporary, TARGET)
    finally:
        Path(temporary).unlink(missing_ok=True)

    print(f'wrote {TARGET}  {len(html)/1024/1024:.2f} MB')
    for k, v in parts.items():
        print(f'  {k.lower():<9} {len(v):3d}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
