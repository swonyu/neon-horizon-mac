"""Colour-space helpers shared by the asset preparation steps.

The foreground grade adjusts Oklab lightness and chroma after decoding sRGB.
Sampling uses gamma-encoded Rec.709 luma, and the approximate preview bloom
uses sRGB to follow CSS filter-function semantics.
"""
import numpy as np

# sRGB <-> linear -------------------------------------------------------------


def srgb_to_linear(x):
    x = np.asarray(x, np.float32)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x):
    x = np.clip(np.asarray(x, np.float32), 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


# linear sRGB <-> Oklab -------------------------------------------------------

_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                [0.2119034982, 0.6806995451, 0.1073969566],
                [0.0883024619, 0.2817188376, 0.6299787005]], np.float32)
_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                [1.9779984951, -2.4285922050, 0.4505937099],
                [0.0259040371, 0.7827717662, -0.8086757660]], np.float32)
_M1_INV = np.linalg.inv(_M1).astype(np.float32)
_M2_INV = np.linalg.inv(_M2).astype(np.float32)


def linear_to_oklab(rgb):
    lms = rgb @ _M1.T
    lms = np.cbrt(np.maximum(lms, 0.0))
    return lms @ _M2.T


def oklab_to_linear(lab):
    lms = lab @ _M2_INV.T
    lms = lms ** 3
    return lms @ _M1_INV.T


# sampling --------------------------------------------------------------------


def luma8(rgb_srgb):
    """Rec.709 luma on 0..255 gamma-encoded values, matching the critique's sampler."""
    a = np.asarray(rgb_srgb, np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def saturation(rgb_srgb):
    a = np.asarray(rgb_srgb, np.float32)
    mx = a.max(-1)
    mn = a.min(-1)
    return np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)


def box(arr, x0, y0, x1, y1):
    """Crop by percentage of frame."""
    h, w = arr.shape[:2]
    return arr[int(h * y0 / 100):int(h * y1 / 100), int(w * x0 / 100):int(w * x1 / 100)]


def report(arr8, name, x0, y0, x1, y1):
    region = box(arr8, x0, y0, x1, y1)
    lum = luma8(region)
    sat = saturation(region / 255.0)
    return {
        'name': name,
        'p05': float(np.percentile(lum, 5)),
        'p95': float(np.percentile(lum, 95)),
        'mean': float(lum.mean()),
        'sat': float(sat.mean()),
    }


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)
