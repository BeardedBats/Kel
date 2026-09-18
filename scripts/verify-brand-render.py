#!/usr/bin/env python3
"""Verify that the canonical Kel logo actually renders in captured UI screenshots.

Masked normalized cross-correlation of the canonical mark against every PNG in a directory:
the mark is rendered at several sizes on both light and dark backgrounds (the UI themes), and each
screenshot is scored at each size. A high score means the exact artwork is present, not a similar
shape.

Usage:
    python scripts/verify-brand-render.py <dir-with-pngs> [--min-score 0.55] [--sizes 32,48,64,96,128]

Exit code 0 if at least one screenshot matched at/above the threshold, 1 otherwise.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import numpy as np
    from PIL import Image
except ImportError:  # pragma: no cover
    print("ERROR: numpy + Pillow required")
    raise SystemExit(2)

REPO = Path(__file__).resolve().parents[1]
CANON = REPO / "desktop/resources/branding/kel-logo.png"


def correlate(img: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """'valid' cross-correlation via FFT."""
    fh, fw = img.shape[0] - kernel.shape[0] + 1, img.shape[1] - kernel.shape[1] + 1
    if fh <= 0 or fw <= 0:
        return np.zeros((0, 0), dtype=np.float64)
    shape = (img.shape[0] + kernel.shape[0] - 1, img.shape[1] + kernel.shape[1] - 1)
    fi = np.fft.rfft2(img, shape)
    fk = np.fft.rfft2(kernel[::-1, ::-1], shape)
    full = np.fft.irfft2(fi * fk, shape)
    return full[kernel.shape[0] - 1 : kernel.shape[0] - 1 + fh,
                kernel.shape[1] - 1 : kernel.shape[1] - 1 + fw]


def templates(sizes: list[int]) -> list[tuple[int, str, np.ndarray, np.ndarray]]:
    art = Image.open(CANON).convert("RGBA")
    bbox = art.getchannel("A").getbbox()
    art = art.crop(bbox) if bbox else art
    out = []
    for size in sizes:
        s = art.copy()
        s.thumbnail((size, size), Image.LANCZOS)
        for bg_name, bg in (("light", (255, 255, 255)), ("dark", (26, 26, 26))):
            canvas = Image.new("RGB", (size, size), bg)
            canvas.paste(s, ((size - s.width) // 2, (size - s.height) // 2), s)
            gray = np.asarray(canvas.convert("L"), dtype=np.float64)
            mask = np.zeros((size, size), dtype=np.float64)
            alpha = np.asarray(Image.new("L", (size, size), 0), dtype=np.float64)
            alpha_box = Image.new("L", (size, size), 0)
            alpha_box.paste(s.getchannel("A"), ((size - s.width) // 2, (size - s.height) // 2))
            alpha = np.asarray(alpha_box, dtype=np.float64) / 255.0
            mask = (alpha > 0.35).astype(np.float64)
            if mask.sum() < 16:
                continue
            out.append((size, bg_name, gray, mask))
    return out


def score_template(image: np.ndarray, tmpl_gray: np.ndarray, mask: np.ndarray) -> float:
    n = mask.sum()
    t = tmpl_gray * mask
    t_mean = t.sum() / n
    tc = (tmpl_gray - t_mean) * mask
    t_var = float((tc * tc).sum())
    if t_var <= 1e-6:
        return 0.0
    s_a = correlate(image, mask)
    s_a2 = correlate(image * image, mask)
    cov = correlate(image, tc)
    mean_a = s_a / n
    var_a = np.maximum(s_a2 - n * mean_a * mean_a, 0.0)
    denom = np.sqrt(var_a * t_var)
    with np.errstate(divide="ignore", invalid="ignore"):
        ncc = np.where(denom > 1e-6, cov / denom, 0.0)
    return float(ncc.max()) if ncc.size else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("directory")
    ap.add_argument("--min-score", type=float, default=0.55)
    ap.add_argument("--sizes", default="32,48,64,96,128")
    args = ap.parse_args()
    if not CANON.exists():
        print(f"canonical logo missing: {CANON}")
        return 2
    sizes = [int(s) for s in args.sizes.split(",") if s.strip()]
    tmpls = templates(sizes)
    files = sorted(Path(args.directory).glob("*.png"))
    if not files:
        print(f"no PNGs in {args.directory}")
        return 1
    print(f"canonical: {CANON.name}  templates: {len(tmpls)} (sizes {sizes} x light/dark)")
    hits, best_overall = [], (0.0, None)
    for f in files:
        img = np.asarray(Image.open(f).convert("L"), dtype=np.float64)
        best = (0.0, None, None)
        for size, bg, gray, mask in tmpls:
            if size + 4 > min(img.shape):
                continue
            s = score_template(img, gray, mask)
            if s > best[0]:
                best = (s, size, bg)
        flag = "MATCH" if best[0] >= args.min_score else "     "
        print(f"  {flag} {f.name:38s} best={best[0]:.3f} size={best[1]} bg={best[2]}")
        if best[0] >= args.min_score:
            hits.append(f.name)
        if best[0] > best_overall[0]:
            best_overall = (best[0], f.name)
    print(f"\nbest overall: {best_overall[0]:.3f} ({best_overall[1]})")
    print(f"matches >= {args.min_score}: {len(hits)}/{len(files)}")
    for h in hits:
        print(f"  - {h}")
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
