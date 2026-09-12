#!/usr/bin/env python3
"""Source-driven framing checks; no browser, services or preferences are touched."""
from html.parser import HTMLParser
from itertools import product
import math
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'wallpaper/build'))
import build
import scatter
import scene

css = re.sub(r'/\*.*?\*/', '', scene.CSS.template, flags=re.S)


def block(selector, source=None):
    source = css if source is None else source
    matches = list(re.finditer(re.escape(selector) + r'\s*\{', source))
    assert len(matches) == 1, f'Expected one unambiguous {selector} rule'
    start = matches[0].end()
    depth = 1
    for end in range(start, len(source)):
        depth += (source[end] == '{') - (source[end] == '}')
        if depth == 0:
            return source[start:end]
    raise AssertionError('Unclosed rule: ' + selector)


def declarations(text):
    return dict(part.strip().split(':', 1) for part in text.split(';') if ':' in part)


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.elements = [], []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        classes = set(attrs.get('class', '').split())
        self.elements.append((classes, attrs, list(self.stack)))
        if tag not in ('meta', 'img', 'br', 'link', 'input', 'hr'):
            self.stack.append(classes)

    def handle_endtag(self, tag):
        self.stack.pop()


def check():
    camera, world = declarations(block('.camera')), declarations(block('.world'))
    assert camera['inset'] == '0' and camera['container-type'] == 'size'
    assert camera.get('transform', 'none') == 'none', 'Camera must not add an untested scale'
    assert world['top'] == world['left'] == '50%' and 'bottom' not in world
    assert world['overflow'] == 'hidden', 'Clip moving effects at the painting boundary'
    width = re.fullmatch(r'min\(([\d.]+)cqw,\s*([\d.]+)cqh\)', world['width'])
    assert width, 'Use a continuous fit of both viewport dimensions'
    width_factor, height_factor = (float(value) / 100 for value in width.groups())
    aspect_width, aspect_height = map(float, world['aspect-ratio'].split('/'))
    aspect = aspect_width / aspect_height
    assert aspect == 1.5 and 1 <= width_factor <= 1.02 + 1e-9
    assert math.isclose(height_factor / aspect, width_factor), 'Overscan must match on both axes'
    drift = block('@keyframes drift')
    positions = re.findall(r'translate3d\(([-\d.]+)%,\s*([-\d.]+)%,\s*0\)', drift)
    assert len(positions) >= 3
    xs, ys = zip(*[(float(x) / 100, float(y) / 100) for x, y in positions])
    assert max(abs(x + .5) for x in xs) <= .003
    assert max(abs(y + .5) for y in ys) <= .001
    # Control points within [0,1] keep interpolation inside the endpoint bounds.
    for values in re.findall(r'cubic-bezier\(([^)]+)\)', drift):
        assert all(0 <= float(value) <= 1 for value in values.split(','))

    def size(vw, vh):
        width = min(width_factor * vw, height_factor * vh)
        return width, width / aspect

    for boundary in (height_factor / width_factor, 1.829):
        before, after = size(boundary - 1e-7, 1), size(boundary + 1e-7, 1)
        assert max(abs(a - b) for a, b in zip(before, after)) < 1e-6, 'Frame jumps across aspect ratios'

    sail = [(float(x) / 100, float(y) / 100) for x, y in
            re.findall(r'translate\(([-\d.]+)%,\s*([-\d.]+)%\)', block('@keyframes sail'))]
    assert len(sail) >= 2 and declarations(block('.boat-anchor'))['transform'] == 'translate(-50%,-50%)'
    assert declarations(block('.boat-art'))['aspect-ratio'] == '3/1'
    bob = block('@keyframes bob')
    bob_y = max(abs(float(value)) for value in re.findall(r'translateY\(([-\d.]+)px\)', bob))
    angle = math.radians(max(abs(float(value)) for value in re.findall(r'rotate\(([-\d.]+)deg\)', bob)))
    scales = [float(value) for value in re.findall(r'scale\(([\d.]+)\)', block('@keyframes dolly'))]
    assert declarations(block('.plane-near'))['transform-origin'] == '50% 100%'
    doc = Elements()
    doc.feed(scene.DOC.template)
    falls = [declarations(attrs['style']) for classes, attrs, _ in doc.elements if 'cascade' in classes]
    assert len(build.BOATS) == len(falls) == len(scatter.PEAKS) == 2

    for ratio in (9 / 16, 1.5, 1.6, 16 / 9, 21 / 9, 32 / 9):
        vw, vh = ratio * 1000, 1000
        ww, wh = size(vw, vh)
        for dx, dy in product((min(xs), max(xs)), (min(ys), max(ys))):
            left, top = vw / 2 + dx * ww, vh / 2 + dy * wh

            def visible(x0, y0, x1, y1, label):
                assert 0 <= left + x0 <= left + x1 <= vw, f'{label} cropped horizontally at {ratio:g}'
                assert 0 <= top + y0 <= top + y1 <= vh, f'{label} cropped vertically at {ratio:g}'

            for boat in build.BOATS:
                bw, bh = boat['width'] / 100 * ww, boat['width'] / 100 * ww / 3
                rx = (bw * math.cos(angle) + bh * math.sin(angle)) / 2
                ry = (bh * math.cos(angle) + bw * math.sin(angle)) / 2 + bob_y
                for sx, sy in sail:
                    cx, cy = boat['left'] / 100 * ww + sx * bw, boat['top'] / 100 * wh + sy * bh
                    visible(cx - rx, cy - ry, cx + rx, cy + ry, 'boat hull')
            for fall in falls:
                x, y, w, h = [float(fall[key].rstrip('%')) / 100 for key in ('left', 'top', 'width', 'height')]
                visible(x * ww, y * wh, (x + w) * ww, (y + h) * wh, 'waterfall')
            for x, y in scatter.PEAKS:
                for scale in (min(scales), max(scales)):
                    px, py = (.5 + (x / 100 - .5) * scale) * ww, (1 + (y / 100 - 1) * scale) * wh
                    visible(px, py, px, py, 'painted puddle center')
    print('PASS: continuous framing and complete boat paths, falls and puddle centers at six aspect ratios')

    # Locate the stationary mask by its actual gradient, independent of its class name.
    regions = re.findall(r'((?:\.[\w-]+)+)\s*\{([^{}]*mask-image:linear-gradient\((?:180deg|to bottom),transparent 0 ([\d.]+)%,#000 ([\d.]+)%\)[^{}]*)\}', css)
    assert len(regions) == 1, 'Expected one stationary near-rain region'
    selector, region, clear, solid = regions[0]
    region_classes = set(re.findall(r'\.([\w-]+)', selector))
    region_style = declarations(region)
    assert region_style['inset'] == '0' and not any(key.startswith(('transform', 'animation')) for key in region_style)
    assert not re.search(r'[\d.](?:vh|vw|vmin|vmax)\b', region), 'Mask must use painting coordinates'
    assert 0 <= .29 <= float(clear) / 100 < float(solid) / 100 <= 1, 'Near rain reaches the painted sun'
    assert declarations(block('.rain.near'))['mask-image'] == 'none', 'Keep the moving gust separate from its mask'
    assert sum(region_classes <= classes for classes, _, _ in doc.elements) == 1
    assert sum('rain' in classes for classes, _, _ in doc.elements) == 4
    for classes, _, ancestors in doc.elements:
        if region_classes <= classes:
            assert any('world' in parent for parent in ancestors), 'Mask must follow the same frame as the painting'
        if 'rain' in classes:
            assert any('world' in parent for parent in ancestors), 'Weather is outside painting coordinates'
            if 'near' in classes:
                assert any(region_classes <= parent for parent in ancestors), 'Near rain is outside its stationary mask'
    print('PASS: painting-relative weather and a stationary near-rain mask excluding the sun at every aspect ratio')

    assert world['container-type'] == 'inline-size', 'Descendant rain units must resolve against the painting'
    rain, drops = declarations(block('.rain')), declarations(block('.rain::before'))
    assert drops['background-size'] == 'var(--tile) var(--tile)'
    assert drops['inset'] == 'calc(-1 * var(--tile)) 0 0'
    assert 'translate3d(0,var(--tile),0)' in block('@keyframes rainfall-lg'), 'Travel must equal one rendered tile'
    relative_scales = []
    for name, tile in build.rain_tiles.TILES.items():
        variant = declarations(block('.rain.' + name, css.split('@media')[0]))
        rendered = re.fullmatch(r'([\d.]+)cqw', variant.get('--tile', rain['--tile']))
        assert rendered, 'Rain tiles must scale with the painting'
        relative_scales.append(float(rendered[1]) / tile['size'])
    assert all(math.isclose(scale, relative_scales[0]) for scale in relative_scales), 'Rain depths use inconsistent image scale'
    print('PASS: proportional rain tiles, one-period overscan and seamless one-period travel')


if __name__ == '__main__':
    check()
