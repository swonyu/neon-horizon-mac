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

    page = (ROOT / 'wallpaper/index.html').read_text()
    assets = [base64.b64decode(data, validate=True) for data in
              re.findall(r'data:image/webp;base64,([A-Za-z0-9+/=]+)', page)]
    names = ('city.webp', 'boat.webp', 'city-blur.webp')
    assert len(assets) == len(names)
    with tempfile.TemporaryDirectory(prefix='neon-build-check-') as folder:
        directory = Path(folder)
        for name, data in zip(names, assets):
            (directory / name).write_bytes(data)
        target = directory / 'index.html'
        with patch.object(build, 'OUT', directory), patch.object(build, 'TARGET', target), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            assert build.main() == 0
            first = target.read_bytes()
            assert build.main() == 0 and target.read_bytes() == first, 'Repeated builds changed placements'
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
    print('PASS: repeated builds, missing-asset preflight and atomic publication failure')

    try:
        import prepare_images
    except ModuleNotFoundError as error:
        if error.name not in ('numpy', 'PIL'):
            raise
        print('SKIP: grading failure preservation requires Pillow and numpy')
        return
    with tempfile.TemporaryDirectory(prefix='neon-grade-check-') as folder:
        directory = Path(folder)
        out = directory / 'out'
        out.mkdir()
        for name in (*names, 'city-graded.png'):
            (out / name).write_bytes(b'previous asset')
        (directory / 'still.png').write_bytes(b'previous still')
        previous = {path: path.read_bytes() for path in directory.rglob('*') if path.is_file()}
        # Zero knockdown fails the real p95 gate on the real source painting.
        with patch.object(prepare_images, 'OUT', out), patch.object(prepare_images, 'HERE', directory / 'build'), patch.object(prepare_images, 'LUMA_DROP', 0), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            assert prepare_images.main() == 1
        assert {path: path.read_bytes() for path in directory.rglob('*') if path.is_file()} == previous, 'A rejected grade replaced output files'
    print('PASS: rejected image grade preserves every previous output')


if __name__ == '__main__':
    check()
