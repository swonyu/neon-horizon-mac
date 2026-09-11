"""W0 steps 1, 4, 5: bake the foreground value knockdown, then encode the assets.

The painting's brightest pixels are the wet foreground pavement, which out-punches
the sunset at both ends of the histogram, so the composition has no value
hierarchy and the eye lands on empty stone. This bakes a feathered knockdown into
the lower-left quadrant so the sky outranks the pavement, then re-encodes both
assets to WebP.

Gate (checked and printed by this script, not asserted by eye):
  promenade p95   162.6 -> 120..130
  promenade p05   stays <= 5            (blacks must not lift)
  sky            unchanged within +/-1
  and the real one: sky p95 must EXCEED promenade p95.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imagelab as il  # noqa: E402

HERE = Path(__file__).resolve().parent
SRC = HERE / 'src'
OUT = HERE / 'out'

PROMENADE = (5, 70, 35, 100)   # x0, y0, x1, y1 in percent
SKY = (35, 15, 65, 40)

# Knockdown geometry, in fractions of image width/height.
# The vertical radius is deliberately tight: the roadmap's 0.95 put 30% of the
# knockdown into the sky box, which the "sky unchanged" gate exists to prevent.
CENTRE = (0.10, 1.05)
RADII = (1.20, 0.62)
LUMA_DROP = 0.20
CHROMA_DROP = 0.10
FEATHER_START = 0.62   # mask is full strength inside this fraction of the radius


def knockdown_mask(h, w):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = (xx / w - CENTRE[0]) / RADII[0]
    dy = (yy / h - CENTRE[1]) / RADII[1]
    r = np.sqrt(dx * dx + dy * dy)
    # 1.0 inside FEATHER_START, smoothly to 0.0 at r = 1.
    t = (1.0 - r) / (1.0 - FEATHER_START)
    return il.smoothstep(t)


def apply_knockdown(img):
    a = np.asarray(img.convert('RGB'), np.float32) / 255.0
    h, w = a.shape[:2]
    mask = knockdown_mask(h, w)

    lin = il.srgb_to_linear(a)
    lab = il.linear_to_oklab(lin)
    dim = 1.0 - LUMA_DROP * mask
    # a/b must follow L, or relative chroma RISES as the area darkens: Oklab
    # chroma is absolute, so holding a/b fixed under a dimmed L makes the
    # pavement read as more saturated, not less. Scale by `dim` to hold relative
    # chroma constant, then by the desaturation term to actually pull it down.
    lab[..., 0] *= dim
    lab[..., 1] *= dim * (1.0 - CHROMA_DROP * mask)
    lab[..., 2] *= dim * (1.0 - CHROMA_DROP * mask)
    out = il.linear_to_srgb(il.oklab_to_linear(lab))
    return Image.fromarray((np.clip(out, 0, 1) * 255).round().astype(np.uint8))


# Mirrors .bloom's CSS filter chain, in the same order and the same (sRGB) space:
# brightness -> contrast -> saturate -> blur, screened back at .2.
BLOOM_BRIGHTNESS = 1.5
BLOOM_CONTRAST = 2.6
BLOOM_SATURATE = 1.25
BLOOM_SIGMA = 17          # CSS blur(5px) at 25% scale, scaled 4x, in source pixels
BLOOM_ALPHA = 0.20


def apply_bloom(img):
    from PIL import ImageFilter
    a = np.asarray(img.convert('RGB'), np.float32) / 255.0
    b = a * BLOOM_BRIGHTNESS
    # contrast(k): out = k*in - (k-1)/2. Everything under ~0.205 luma goes to
    # black and contributes nothing under screen, which is what protects the
    # painting's darks.
    b = BLOOM_CONTRAST * b - (BLOOM_CONTRAST - 1) / 2
    b = np.clip(b, 0, 1)
    lum = il.luma8(b * 255.0)[..., None] / 255.0
    b = np.clip(lum + (b - lum) * BLOOM_SATURATE, 0, 1)
    blurred = Image.fromarray((b * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(BLOOM_SIGMA))
    b = np.asarray(blurred, np.float32) / 255.0
    out = a + BLOOM_ALPHA * b * (1.0 - a)      # screen, at the layer's opacity
    return Image.fromarray((np.clip(out, 0, 1) * 255).round().astype(np.uint8))


def sample(img, label):
    a = np.asarray(img.convert('RGB'), np.float32)
    p = il.report(a, 'promenade', *PROMENADE)
    s = il.report(a, 'sky', *SKY)
    print(f'  {label:<9} promenade p05={p["p05"]:6.1f} p95={p["p95"]:6.1f} '
          f'mean={p["mean"]:6.1f} sat={p["sat"]:.3f}')
    print(f'  {label:<9} sky       p05={s["p05"]:6.1f} p95={s["p95"]:6.1f} '
          f'mean={s["mean"]:6.1f} sat={s["sat"]:.3f}')
    return p, s


def main():
    OUT.mkdir(exist_ok=True)
    city = Image.open(SRC / 'city-source.png')
    print('Value knockdown')
    before_p, before_s = sample(city, 'before')
    graded = apply_knockdown(city)
    after_p, after_s = sample(graded, 'after')

    ok = True
    checks = [
        ('promenade p95 in 120..130', 120 <= after_p['p95'] <= 130),
        ('promenade p05 <= 5 (blacks not lifted)', after_p['p05'] <= 5.0),
        ('sky mean unchanged +/-1', abs(after_s['mean'] - before_s['mean']) <= 1.0),
        ('SKY p95 EXCEEDS PROMENADE p95', after_s['p95'] > after_p['p95']),
    ]
    print('Gates')
    for name, passed in checks:
        print(f'  [{"PASS" if passed else "FAIL"}] {name}')
        ok &= passed

    graded.save(OUT / 'city-graded.png')

    # Step 4: encode. The graded PNG stays as the master for the bloom pass.
    graded.convert('RGB').save(OUT / 'city.webp', quality=90, method=6)
    boat = Image.open(SRC / 'boat-source.png').convert('RGBA')
    # 768x256 is exactly 3:1, matching .boat-art's declared aspect-ratio.
    boat.resize((768, 256), Image.LANCZOS).save(OUT / 'boat.webp', quality=90, method=6)

    for f in ('city.webp', 'boat.webp'):
        print(f'  {f}: {(OUT / f).stat().st_size / 1024:.1f} KB')

    # README preview. Reproduces the CSS bloom offline so the still matches what
    # the page actually renders, rather than showing the ungraded source.
    print('Preview still')
    still = apply_bloom(graded)
    still.save(HERE.parent / 'still.png')
    print(f'  still.png: {(HERE.parent / "still.png").stat().st_size / 1024:.1f} KB')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
