#!/usr/bin/env python3
"""Repeat isolated build timings or explicit read-only native previews; JSON output.

python tests/benchmark.py assembly
python tests/benchmark.py images       # requires Pillow and numpy
python tests/benchmark.py preferences  # reads native preferences; never applies
python tests/benchmark.py dock         # reads app metadata; never applies
python tests/benchmark.py discover     # also reads unpinned app metadata

One discarded warmup, then five fresh processes by default. Build fixtures/imports
are outside operation_seconds, but inside process_seconds. No renderer, live
wallpaper endpoint, UI, native writes, or background monitor is used.
"""
import argparse
import base64
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import resource
import statistics
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def once(task):
    with tempfile.TemporaryDirectory(prefix='neon-benchmark-') as folder:
        directory = Path(folder)
        if task in ('assembly', 'images'):
            sys.path.insert(0, str(ROOT / 'wallpaper/build'))
            if task == 'assembly':
                import build
                page = (ROOT / 'wallpaper/index.html').read_bytes()
                assets = re.findall(rb'data:image/webp;base64,([A-Za-z0-9+/=]+)', page)
                assert len(assets) == 3, 'Expected city, boat and surround assets'
                for name, data in zip(('city.webp', 'boat.webp', 'city-blur.webp'), assets):
                    (directory / name).write_bytes(base64.b64decode(data, validate=True))
                build.OUT, build.TARGET = directory, directory / 'index.html'
                operation = build.main
            else:
                import prepare_images
                prepare_images.OUT = directory / 'out'
                prepare_images.HERE = directory / 'build'
                operation = prepare_images.main
        elif task == 'preferences':
            makeover = module('makeover', ROOT / 'makeover.py')
            settings = makeover.load_settings(['all'])
            operation = lambda: makeover.plan(settings)
        else:
            dock = module('dock', ROOT / 'dock.py')
            operation = lambda: dock.plan(task == 'discover')
        if task in ('preferences', 'dock', 'discover') and sys.platform != 'darwin':
            raise SystemExit('Native previews require macOS')
        started = time.perf_counter()
        with redirect_stdout(io.StringIO()):
            result = operation()
        elapsed = time.perf_counter() - started
        if task in ('assembly', 'images'):
            assert result == 0, 'Build failed'
        if task == 'assembly':
            assert build.TARGET.read_bytes() == page, 'Shipped HTML differs from its source'
        if task == 'images':
            assert (directory / 'still.png').read_bytes() == (ROOT / 'wallpaper/still.png').read_bytes(), 'Reference image encoder differs'
        own = resource.getrusage(resource.RUSAGE_SELF)
        child = resource.getrusage(resource.RUSAGE_CHILDREN)
        return {'operation_seconds': elapsed,
                'process_cpu_seconds': own.ru_utime + own.ru_stime + child.ru_utime + child.ru_stime,
                # Python process peak only; native child peaks are not summed.
                'python_peak_rss_mib': own.ru_maxrss / (1024**2 if sys.platform == 'darwin' else 1024)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task', choices=('assembly', 'images', 'preferences', 'dock', 'discover'))
    parser.add_argument('--runs', type=int, default=5)
    parser.add_argument('--once', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 1 <= args.runs <= 20:
        parser.error('--runs must be between 1 and 20')
    if args.once:
        print(json.dumps(once(args.task)))
        return
    samples = []
    for _ in range(args.runs + 1):
        start = time.perf_counter()
        process = subprocess.run([sys.executable, str(Path(__file__).resolve()), args.task, '--once'],
                                 check=True, capture_output=True, text=True, timeout=300)
        sample = json.loads(process.stdout)
        sample['process_seconds'] = time.perf_counter() - start
        samples.append(sample)
    measured = samples[1:]
    print(json.dumps({'task': args.task, 'python': sys.version.split()[0],
                      'wallpaper_sha256': hashlib.sha256((ROOT / 'wallpaper/index.html').read_bytes()).hexdigest(),
                      'warmup': samples[0], 'samples': measured,
                      'summary': {key: {'median': statistics.median(row[key] for row in measured),
                                        'min': min(row[key] for row in measured),
                                        'max': max(row[key] for row in measured)}
                                  for key in measured[0]}}, indent=2))


if __name__ == '__main__':
    main()
