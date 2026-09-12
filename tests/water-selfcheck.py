#!/usr/bin/env python3
"""Check emitted placements against inspected painting surfaces; no renderer or raster edits."""
from html.parser import HTMLParser
import importlib.util
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('scatter', ROOT / 'wallpaper/build/scatter.py')
scatter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scatter)

# Independent source-image coordinates from the visual audit, not inferred from generated data.
WATER = ((815, 505, 830, 536), (821, 576, 838, 617),
         (895, 710, 958, 750), (1315, 890, 1470, 955))
WINDOWS = ((728, 726), (728, 746), (796, 692), (796, 700),
           (793, 706), (1300, 591), (648, 483), (651, 496))
FACADES = ((724, 720, 734, 753), (788, 685, 803, 712),
           (1296, 587, 1305, 600), (644, 478, 655, 501))
LAMPS = ((232, 501), (331, 505))


class Markers(HTMLParser):
    def __init__(self, elements):
        super().__init__()
        self.items = []
        self.feed(''.join(elements))

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        style = dict(item.split(':', 1) for item in attributes['style'].split(';') if item)
        self.items.append((attributes['class'], style))


def value(style, key):
    number = float(style[key].rstrip('%s'))
    assert math.isfinite(number)
    return number


def contains(region, bounds):
    x0, y0, x1, y1 = region
    left, top, right, bottom = bounds
    return x0 <= left <= right <= x1 and y0 <= top <= bottom <= y1


def water_placements():
    opaque = soft_mask()
    css = (ROOT / 'wallpaper/build/scene.py').read_text()
    assert 'container-type:inline-size' in re.search(r'\.world\{([^}]+)', css)[1]
    shadow = re.search(r'\.wet\.river \.sp\{box-shadow:([^}]+)', css)[1]
    outer = [layer.strip().split()[:4] for layer in shadow.split(',') if 'inset' not in layer]
    assert len(outer) == 2 and all(layer[:2] == ['0', '0'] for layer in outer)
    assert all(token == '0' or token.endswith('cqw') for layer in outer for token in layer[2:])
    # A cqw is 1% of the source-width container: use the emitted CSS's nominal
    # blur radius + spread. Gaussian blur has faint tails beyond this allowance.
    allowance = max(sum(float(token.rstrip('cqw')) for token in layer[2:]) for layer in outer) * 15.36
    for seed in [20260911, *range(64)]:
        scatter.rng.seed(seed)
        scatter.impact_field()  # Exercise the same random stream order as build.py.
        rings = Markers(scatter.river_impacts()).items
        scatter.smears()
        glints = Markers(scatter.glints()).items
        assert len(rings) == 14
        assert len(glints) == 30, len(glints)
        counts = [0] * 4
        widths = [[] for _ in WATER]
        heights = [[] for _ in WATER]
        for kind, style in glints:
            assert kind == 'glint'
            x, y = value(style, 'left') * 15.36, value(style, 'top') * 10.24
            w, h = value(style, 'width') * 15.36, value(style, '--gh') * 10.24
            # CSS scales height to 1.5 around the element center; left/top are not centered.
            bounds = (x, y - .25 * h, x + w, y + 1.25 * h)
            matches = [i for i, region in enumerate(opaque) if contains(region, bounds)]
            assert len(matches) == 1, (seed, bounds)
            counts[matches[0]] += 1
            widths[matches[0]].append(w)
            heights[matches[0]].append(h)
            assert value(style, '--gt') > 0 and value(style, '--delay') <= 0
            if matches[0] < 2:
                assert style['--c'] in ('#ffe6cf', '#ffb27f', '#f9becb')
        assert counts == [6, 6, 8, 10], counts
        assert max(widths[0]) < min(widths[3])
        assert all(max(heights[i]) < min(heights[i + 1]) for i in range(3))
        counts = [0, 0]
        for kind, style in rings:
            assert kind == 'sp'
            x, y = value(style, 'left') * 15.36, value(style, 'top') * 10.24
            w, h = value(style, '--w') * 15.36, value(style, '--h') * 10.24
            # End scale is 1; include the nominal source-scaled outer shadow.
            bounds = (x - w / 2 - allowance, y - h / 2 - allowance,
                      x + w / 2 + allowance, y + h / 2 + allowance)
            matches = [i for i, region in enumerate(opaque[2:]) if contains(region, bounds)]
            assert len(matches) == 1, (seed, bounds)
            counts[matches[0]] += 1
            assert value(style, '--p') > 0 and value(style, '--d') <= 0
        assert counts == [6, 8], counts
    old_bad_points = [(1029, 715), (1036, 630), (774, 663), (785, 676), (814, 410),
                      (898, 978), (1021, 955)]
    assert not any(contains(region, (x, y, x, y)) for x, y in old_bad_points for region in WATER)


def fixed_source_anchors():
    for function, kind, expected in [(scatter.windows, 'win', WINDOWS), (scatter.lamps, 'lamp', LAMPS)]:
        items = [(cls, style) for cls, style in Markers(function()).items if cls.split()[0] == kind]
        assert len(items) == len(expected), (kind, len(items))
        for (_, style), (x, y) in zip(items, expected):
            actual = (value(style, 'left') * 15.36, value(style, 'top') * 10.24)
            assert abs(actual[0] - x) < .1 and abs(actual[1] - y) < .1, (kind, actual, (x, y))
            assert value(style, '--wt' if kind == 'win' else '--lt') > 0
            assert value(style, '--d') <= 0
            if kind == 'win':
                # Centered .28%-wide, .42%-high patches stay within inspected facade interiors.
                dx, dy = .0028 * 1536 / 2, .0042 * 1024 / 2
                assert any(contains(region, (actual[0] - dx, actual[1] - dy,
                                             actual[0] + dx, actual[1] + dy)) for region in FACADES)
    streaks = [style for cls, style in Markers(scatter.lamps()).items if cls == 'lamp-streak']
    assert len(streaks) == 2
    assert value(streaks[0], 'top') != value(streaks[1], 'top')


def soft_mask():
    assert tuple(scatter.WATER_REGIONS) == WATER
    state = scatter.rng.getstate()
    svg = ET.fromstring(scatter.water_mask())
    assert scatter.rng.getstate() == state
    assert svg.attrib['viewBox'] == '0 0 1536 1024'
    ns = {'s': 'http://www.w3.org/2000/svg'}
    gradients = svg.findall('./s:defs/s:linearGradient', ns)
    assert len(gradients) == 2, 'Mask needs horizontal and vertical rectangular edge fades'
    opaque = {}
    axes = {}
    for gradient in gradients:
        assert gradient.get('gradientUnits', 'objectBoundingBox') == 'objectBoundingBox'
        assert 'gradientTransform' not in gradient.attrib
        stops = gradient.findall('s:stop', ns)
        offsets = [float(stop.attrib['offset'].rstrip('%')) / 100 for stop in stops]
        opacity = [float(stop.get('stop-opacity', '1')) for stop in stops]
        assert offsets == [0, .05, .95, 1] and opacity == [0, 1, 1, 0]
        assert all(stop.attrib['stop-color'] in ('white', '#fff', '#ffffff') for stop in stops)
        opaque[gradient.attrib['id']] = (offsets[1], offsets[2])
        axes[gradient.attrib['id']] = tuple(gradient.attrib[k] for k in ('x1', 'y1', 'x2', 'y2'))
    masks = svg.findall('./s:defs/s:mask', ns)
    assert len(masks) == 1
    mask = masks[0]
    assert mask.attrib['maskUnits'] == mask.attrib['maskContentUnits'] == 'objectBoundingBox'
    assert tuple(mask.attrib[k] for k in ('x', 'y', 'width', 'height')) == ('0', '0', '1', '1')
    mask_rectangles = mask.findall('s:rect', ns)
    assert len(mask_rectangles) == 1
    mask_rectangle = mask_rectangles[0]
    assert (mask_rectangle.get('x', '0'), mask_rectangle.get('y', '0'),
            mask_rectangle.attrib['width'], mask_rectangle.attrib['height']) == ('0', '0', '1', '1')
    vertical_id = re.fullmatch(r'url\(#([^)]*)\)', mask_rectangle.attrib['fill'])[1]
    assert axes[vertical_id] == ('0%', '0%', '0%', '100%')
    rectangles = svg.findall('s:rect', ns)
    actual = []
    cores = []
    for rect in rectangles:
        x, y, w, h = (float(rect.attrib[key]) for key in ['x', 'y', 'width', 'height'])
        actual.append((x, y, x + w, y + h))
        horizontal_id = re.fullmatch(r'url\(#([^)]*)\)', rect.attrib['fill'])[1]
        assert axes[horizontal_id] == ('0%', '0%', '100%', '0%')
        assert rect.attrib['mask'] == 'url(#' + mask.attrib['id'] + ')'
        u0, u1 = opaque[horizontal_id]
        v0, v1 = opaque[vertical_id]
        # Horizontal fill alpha multiplied by the vertical SVG mask is fully
        # opaque only in this rectangle, not throughout the outer water region.
        cores.append((x + w * u0, y + h * v0, x + w * u1, y + h * v1))
    assert actual == list(WATER)
    return cores


def repeatable_assembly():
    def assemble():
        scatter.rng.seed(20260911)
        return [function() for function in [scatter.impact_field, scatter.river_impacts, scatter.smears,
                                           scatter.glints, scatter.traffic, scatter.lamps, scatter.windows,
                                           scatter.water_mask]]
    assert assemble() == assemble()
    css = (ROOT / 'wallpaper/build/scene.py').read_text()
    flare = re.search(r'@keyframes flare\{([^\n]+)', css)[1]
    assert max(map(float, re.findall(r'scaleY\(([\d.]+)\)', flare))) == 1.5


if __name__ == '__main__':
    failures = []
    for check in [water_placements, fixed_source_anchors, soft_mask, repeatable_assembly]:
        try:
            check()
            print('PASS:', check.__name__)
        except Exception as error:
            failures.append(check.__name__)
            print('FAIL:', check.__name__, type(error).__name__, str(error))
    assert not failures, failures
