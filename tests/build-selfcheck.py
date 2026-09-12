#!/usr/bin/env python3
"""Offline wallpaper checks; image grading also runs when Pillow/numpy exist."""
import base64
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import re
import sys
import tempfile
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'wallpaper/build'))
import build
import scene

ASSET_NAMES = ('city.webp', 'boat.webp', 'city-blur.webp')
STALE_HTML = 'Generated wallpaper differs from wallpaper/index.html; rebuild before shipping'


def check():
    css = scene.CSS.template
    base = re.search(r'\.boat-reflection\{([^}]*)', css).group(1)
    frames = re.search(r'@keyframes reflection\{(.*?)\}\}', css, re.S).group(1)
    transforms = re.findall(r'transform:([^;}]+)', base + frames)
    assert len(transforms) == 3
    waterline = float(re.search(r'top:([\d.]+)%', base).group(1)) / 100
    for transform in transforms:
        match = re.fullmatch(r'scaleY\((-[\d.]+)\) translateY\(-100%\)', transform)
        assert match, f'Reflection must flip below its waterline: {transform}'
        scale = float(match.group(1))
        # CSS applies the rightmost translation before scaling about the top.
        assert min(waterline + scale * (y - 1) for y in (0, 1)) >= waterline
    reduced = css.split('@media(prefers-reduced-motion:reduce){', 1)[1]
    assert not re.search(r'\.(?:light|haze\.[hmf])\{', reduced), 'Keep the storm-scaled static baseline'
    print('PASS: reflection geometry and reduced-motion atmospheric baseline')

    # The mask must stay still while a whole texture period passes beneath it.
    shimmer = re.search(r'\.glit\{([^}]*)', css).group(1)
    stripe = re.search(r'\.glit::before\{([^}]*)', css).group(1)
    travel = float(re.search(r'@keyframes crawl\{to\{transform:translateY\(([\d.]+)px\)', css).group(1))
    period = float(re.search(r'transparent ([\d.]+)px\)', stripe).group(1))
    overscan = float(re.search(r'inset:-([\d.]+)px', stripe).group(1))
    assert travel == period == overscan
    assert 'mask-image:' in shimmer and 'animation:' not in shimmer
    assert 'overflow:hidden' in shimmer and 'mask-image:' not in stripe
    for selector in ('.paused *,.paused *::before,.paused *::after',
                     '*,*::before,*::after'):
        scope = css if selector.startswith('.paused') else reduced
        rule = re.search(re.escape(selector) + r'\{([^}]*)', scope).group(1)
        assert 'will-change:auto!important' in rule
    river = re.search(r'\.wet\.river\{([^}]*)', css).group(1)
    lights = re.search(r'\.water-light\{([^}]*)', css).group(1)
    assert 'mask-image:var(--water-mask)' in river and 'mask-image:var(--water-mask)' in lights
    assert 'mix-blend-mode:screen' in lights and 'mix-blend-mode' not in river
    assert build.EMITTERS[3]['x'] == 75.74 and build.EMITTERS[3]['y'] == 38.02
    print('PASS: stationary shimmer envelope, water clipping and inactive preparation hints')

    check_assembly()
    check_freshness_guard()
    check_grading()


def check_assembly():
    page = (ROOT / 'wallpaper/index.html').read_bytes()
    assets = [base64.b64decode(data, validate=True) for data in
              re.findall(rb'data:image/webp;base64,([A-Za-z0-9+/=]+)', page)]
    names = ASSET_NAMES
    assert len(assets) == len(names)
    with tempfile.TemporaryDirectory(prefix='neon-build-check-') as folder:
        directory = Path(folder)
        for name, data in zip(names, assets):
            (directory / name).write_bytes(data)
        target = directory / 'index.html'
        with patch.object(build, 'OUT', directory), patch.object(build, 'TARGET', target), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            assert build.main() == 0
            first = target.read_bytes()
            assert first == page, STALE_HTML
            assert build.main() == 0 and target.read_bytes() == first, 'Repeated builds changed placements'
            for name in names:
                asset = directory / name
                contents = asset.read_bytes()
                broken = (b'', b'not a WebP', contents[:-1],
                          contents[:4] + (len(contents) + 4).to_bytes(4, 'little') + contents[8:],
                          contents[:4] + (len(contents) - 10).to_bytes(4, 'little') + contents[8:-2],
                          contents[:16] + len(contents).to_bytes(4, 'little') + contents[20:],
                          b'RIFF\x0c\x00\x00\x00WEBPVP8 \x00\x00\x00\x00')
                for data in broken:
                    asset.write_bytes(data)
                    assert build.main() == 1, f'Invalid {name} was accepted'
                    assert target.read_bytes() == first, f'Invalid {name} replaced the wallpaper'
                asset.write_bytes(contents)
            with patch.object(build, 'HERE', directory):
                for data in ('', 'not SVG', 'data:image/svg+xml,%3Csvg',
                             'data:image/svg+xml,%3Chtml/%3E',
                             'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg"/>'):
                    (directory / 'falltile.txt').write_text(data)
                    assert build.main() == 1, 'Invalid waterfall SVG was accepted'
                    assert target.read_bytes() == first, 'Invalid waterfall SVG replaced the wallpaper'
                (directory / 'falltile.txt').unlink()
            for name in names:
                asset = directory / name
                contents = asset.read_bytes()
                asset.unlink()
                assert build.main() == 1 and target.read_bytes() == first, f'Missing {name} changed the target'
                asset.write_bytes(contents)
            with patch.object(build, 'HERE', directory):
                assert build.main() == 1 and target.read_bytes() == first, 'Missing waterfall tile changed the target'
            before = set(directory.iterdir())
            with patch.object(build.os, 'replace', side_effect=OSError('simulated publication failure')):
                try:
                    build.main()
                    raise AssertionError('Publication failure was swallowed')
                except OSError:
                    pass
            assert target.read_bytes() == first, 'Failed publication replaced the old wallpaper'
            assert set(directory.iterdir()) == before, 'Failed publication left a temporary file'
    print('PASS: exact shipped HTML, repeated builds, invalid/missing assets and atomic publication failure')


def check_freshness_guard():
    with patch.object(scene.CSS, 'template', scene.CSS.template + '\n/* source-only freshness probe */'):
        try:
            check_assembly()
        except AssertionError as error:
            assert str(error) == STALE_HTML, f'Unexpected freshness failure: {error}'
        else:
            raise AssertionError('A source-only template change passed the shipped-HTML check')
    print('PASS: source-only template changes fail the shipped-HTML check')


def check_grading():
    try:
        import prepare_images
    except ModuleNotFoundError as error:
        if error.name not in ('numpy', 'PIL'):
            raise
        print('SKIP: image preparation checks require Pillow and numpy')
        return
    with tempfile.TemporaryDirectory(prefix='neon-grade-check-') as folder:
        directory = Path(folder)
        out = directory / 'out'
        out.mkdir()
        for name in (*ASSET_NAMES, 'city-graded.png'):
            (out / name).write_bytes(b'previous asset')
        (directory / 'still.png').write_bytes(b'previous still')
        previous = {path: path.read_bytes() for path in directory.rglob('*') if path.is_file()}
        # Zero knockdown fails the real p95 gate on the real source painting.
        with patch.object(prepare_images, 'OUT', out), patch.object(prepare_images, 'HERE', directory / 'build'), patch.object(prepare_images, 'LUMA_DROP', 0), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            assert prepare_images.main() == 1
        assert {path: path.read_bytes() for path in directory.rglob('*') if path.is_file()} == previous, 'A rejected grade replaced output files'
    print('PASS: rejected image grade preserves every previous output')

    changed = []
    for failure in ('missing boat', 'corrupt boat', 'late encoding failure'):
        with tempfile.TemporaryDirectory(prefix='neon-encode-check-') as folder:
            directory = Path(folder)
            out, source = directory / 'out', directory / 'src'
            out.mkdir()
            source.mkdir()
            for name in ('city-source.png', 'boat-source.png'):
                (source / name).write_bytes((prepare_images.SRC / name).read_bytes())
            for name in (*ASSET_NAMES, 'city-graded.png'):
                (out / name).write_bytes(b'previous asset')
            (directory / 'still.png').write_bytes(b'previous still')
            if failure == 'missing boat':
                (source / 'boat-source.png').unlink()
            elif failure == 'corrupt boat':
                (source / 'boat-source.png').write_bytes(b'not a PNG')
            previous = {path: path.read_bytes() for path in directory.rglob('*') if path.is_file()}
            previous_paths = set(directory.rglob('*'))
            original_save = prepare_images.Image.Image.save

            def save(image, target, *args, **kwargs):
                if failure == 'late encoding failure' and Path(target).name == 'city-blur.webp':
                    raise OSError('simulated final WebP encoding failure')
                return original_save(image, target, *args, **kwargs)

            with patch.object(prepare_images, 'OUT', out), patch.object(prepare_images, 'SRC', source), patch.object(prepare_images, 'HERE', directory / 'build'), patch.object(prepare_images.Image.Image, 'save', save), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                result = prepare_images.main()
            assert result == 1, failure
            if ({path: path.read_bytes() for path in directory.rglob('*') if path.is_file()} != previous
                    or set(directory.rglob('*')) != previous_paths):
                changed.append(failure)
    assert not changed, f'Previous outputs changed or staging remained after: {changed}'
    print('PASS: missing/corrupt source and late encode failure preserve all previous outputs')

    with tempfile.TemporaryDirectory(prefix='neon-prepare-check-') as folder:
        directory = Path(folder)
        out = directory / 'out'
        with patch.object(prepare_images, 'OUT', out), patch.object(prepare_images, 'HERE', directory / 'build'), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            assert prepare_images.main() == 0
            first = {path.relative_to(directory): path.read_bytes()
                     for path in directory.rglob('*') if path.is_file()}
            assert prepare_images.main() == 0
        assert {path.relative_to(directory): path.read_bytes()
                for path in directory.rglob('*') if path.is_file()} == first
        expected = {Path('out/city-graded.png'): (1536, 1024),
                    Path('out/city.webp'): (1536, 1024), Path('out/boat.webp'): (768, 256),
                    Path('out/city-blur.webp'): (64, 43), Path('still.png'): (1536, 1024)}
        assert first.keys() == expected.keys()
        assert [path for path in directory.rglob('*') if path.is_dir()] == [out]
        for path, size in expected.items():
            with prepare_images.Image.open(directory / path) as image:
                image.load()
                assert image.size == size, path
    print('PASS: complete staged preparation, decodable outputs and same-environment repeatability')


if __name__ == '__main__':
    check()
