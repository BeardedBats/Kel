#!/usr/bin/env python3
"""Generate every Kel brand asset from the ONE canonical logo image.

The canonical source is the exact Nick-supplied folded-ribbon K
(`Kel Logo.png`, sha256 7418a42f…). This script never redraws, recolors, crops the mark,
or distorts it: it only (a) trims fully transparent margin, (b) scales uniformly, and
(c) recenters on a transparent square canvas with a uniform inset. All resampling is done
in premultiplied alpha so no dark/black fringe appears on the soft edges.

Usage:
    python scripts/make-brand-assets.py <path-to-canonical.png> [--check]

`--check` verifies the recorded hashes of the generated files without rewriting them.
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    print("ERROR: Pillow is required (pip install pillow)")
    raise SystemExit(2)

try:
    import numpy as np
except ImportError:  # pragma: no cover
    print("ERROR: numpy is required for premultiplied resizing")
    raise SystemExit(2)

REPO = Path(__file__).resolve().parents[1]
CANON_SHA256 = "7418a42fc06267707c1e1aa4ab0d8822e8d636a687a81f200788a7b3e50ec71f"

# canvas size + per-side inset fraction (uniform; aspect ratio is never changed)
ICON_INSET = 0.06
DEV_INSET = 0.15
PWA_INSET = 0.08

OUTPUTS: list[tuple[str, int, float]] = [
    # (repo-relative path, canvas px, inset)
    ("desktop/resources/app.png", 1024, ICON_INSET),
    ("desktop/resources/app_dev.png", 1024, DEV_INSET),
    ("desktop/resources/icon.png", 800, ICON_INSET),
    ("desktop/public/pwa/icon-180.png", 180, PWA_INSET),
    ("desktop/public/pwa/icon-192.png", 192, PWA_INSET),
    ("desktop/public/pwa/icon-512.png", 512, PWA_INSET),
    ("desktop/packages/desktop/src/renderer/assets/logos/brand/app.png", 1024, ICON_INSET),
]

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
ICNS_CHUNKS = [("ic11", 32), ("ic12", 64), ("ic07", 128), ("ic13", 256),
               ("ic08", 256), ("ic14", 512), ("ic09", 512), ("ic10", 1024)]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def art_crop(im: Image.Image) -> Image.Image:
    """Trim fully transparent margin only — never any part of the mark itself."""
    bbox = im.getchannel("A").getbbox()
    return im.crop(bbox) if bbox else im


def render(art: Image.Image, canvas: int, inset: float) -> Image.Image:
    """Uniform scale into a transparent square canvas, premultiplied resampling."""
    inner = max(1, int(round(canvas * (1 - 2 * inset))))
    src = np.asarray(art.convert("RGBA"), dtype=np.float32)
    alpha = src[..., 3:4] / 255.0
    premult = np.concatenate([src[..., :3] * alpha, src[..., 3:4]], axis=-1)
    h, w = premult.shape[:2]
    scale = min(inner / w, inner / h)
    tw, th = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    resized = np.asarray(
        Image.fromarray(premult.clip(0, 255).astype(np.uint8), "RGBA").resize((tw, th), Image.LANCZOS),
        dtype=np.float32,
    )
    a = resized[..., 3:4] / 255.0
    rgb = np.where(a > 0, resized[..., :3] / np.maximum(a, 1e-6), 0.0).clip(0, 255)
    tile = Image.fromarray(np.concatenate([rgb, resized[..., 3:4]], axis=-1).astype(np.uint8), "RGBA")
    out = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    out.paste(tile, ((canvas - tw) // 2, (canvas - th) // 2), tile)
    return out


def write_ico(path: Path, frames: list[Image.Image]) -> None:
    """Minimal PNG-based ICO (Windows Vista+) — full control, no fringe."""
    import io

    payloads = []
    for frame in frames:
        buf = io.BytesIO()
        frame.save(buf, format="PNG", optimize=True)
        payloads.append((frame.width, buf.getvalue()))
    header = struct.pack("<HHH", 0, 1, len(payloads))
    offset = len(header) + 16 * len(payloads)
    directory, body = b"", b""
    for size, data in payloads:
        directory += struct.pack("<BBBBHHII", size if size < 256 else 0, size if size < 256 else 0,
                                 0, 0, 1, 32, len(data), offset)
        body += data
        offset += len(data)
    path.write_bytes(header + directory + body)


def write_icns(path: Path, frames: list[tuple[str, Image.Image]]) -> None:
    """Minimal ICNS writer using PNG chunks (macOS 10.7+)."""
    import io

    body = b""
    for ctype, frame in frames:
        buf = io.BytesIO()
        frame.save(buf, format="PNG", optimize=True)
        data = buf.getvalue()
        body += ctype.encode("ascii") + struct.pack(">I", len(data) + 8) + data
    path.write_bytes(b"icns" + struct.pack(">I", len(body) + 8) + body)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    source = Path(sys.argv[1]).resolve()
    check = "--check" in sys.argv[2:]
    digest = sha256(source)
    if digest != CANON_SHA256:
        print(f"REFUSED: {source} sha256 {digest}\n         expected {CANON_SHA256}")
        print("         (only the exact canonical Kel logo may generate brand assets)")
        return 1
    art = art_crop(Image.open(source).convert("RGBA"))

    produced: list[tuple[str, str]] = []
    if not check:
        # 1) preserve the canonical source unchanged inside the repo
        canon = REPO / "desktop/resources/branding/kel-logo.png"
        canon.parent.mkdir(parents=True, exist_ok=True)
        canon.write_bytes(source.read_bytes())
        produced.append(("desktop/resources/branding/kel-logo.png", digest))
        # 2) raster derivatives
        for rel, canvas, inset in OUTPUTS:
            out = REPO / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            render(art, canvas, inset).save(out, format="PNG", optimize=True)
        # 3) Windows ICO
        ico = REPO / "desktop/resources/app.ico"
        write_ico(ico, [render(art, s, ICON_INSET) for s in ICO_SIZES])
        # 4) macOS ICNS
        write_icns(REPO / "desktop/resources/app.icns",
                   [(t, render(art, s, ICON_INSET)) for t, s in ICNS_CHUNKS])

    for rel, canvas, _ in OUTPUTS:
        produced.append((rel, sha256(REPO / rel)))
    produced.append(("desktop/resources/app.ico", sha256(REPO / "desktop/resources/app.ico")))
    produced.append(("desktop/resources/app.icns", sha256(REPO / "desktop/resources/app.icns")))
    print(f"canonical : {source}  sha256 {digest}")
    width = max(len(rel) for rel, _ in produced)
    for rel, dg in produced:
        print(f"  {rel.ljust(width)}  {dg}")
    print("check mode — no files written" if check else f"wrote {len(produced)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
