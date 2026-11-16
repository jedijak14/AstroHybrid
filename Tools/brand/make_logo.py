#!/usr/bin/env python3
"""Generate the AstroHybrid app icon (PNG + multi-resolution ICO).

The mark is a flat, two-colour emblem: a warm off-white planet with a violet
ring, on a near-black rounded tile, plus a small sparkle. Solid fills only -
no gradients, glow or shadow - so it stays crisp at 16 px and does not look
like generated artwork.

Usage:
    python3 Tools/brand/make_logo.py
Writes:
    AstroHybrid.App/Resources/astrohybrid.png        (512 px, tile - exe, docs)
    AstroHybrid.App/Resources/astrohybrid-mark.png   (512 px, transparent - UI)
    AstroHybrid.App/Resources/astrohybrid.ico        (16-256 px, window/exe icon)
    Docs/images/astrohybrid-logo.png                 (documentation preview)

The transparent "mark" exists because the tile is the same near-black as the
launcher's sidebar and hero plate, so a tiled image would disappear there.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
APP_RES = ROOT / "AstroHybrid.App" / "Resources"
DOC_IMAGES = ROOT / "Docs" / "images"

S = 2048  # master canvas, downsampled from here

TILE = (14, 18, 26)          # #0E121A
PLANET = (246, 242, 227)     # #F6F2E3 warm off-white
RING = (139, 124, 255)       # #8B7CFF violet
SPARKLE = (169, 155, 255)    # #A99BFF

TILT = -18.0                 # degrees, ring tilt


def sparkle(cx: float, cy: float, r: float, waist: float = 0.30) -> list[tuple[float, float]]:
    """Four-point star with concave sides."""
    pts = []
    for i in range(8):
        angle = -math.pi / 2 + i * math.pi / 4
        k = 1.0 if i % 2 == 0 else waist
        pts.append((cx + r * k * math.cos(angle), cy + r * k * math.sin(angle)))
    return pts


def ring_band(size: int, *, lower_half_only: bool) -> Image.Image:
    """The ring as a flat band, tilted, optionally only its front (lower) half."""
    rx, ry, thick = size * 0.355, size * 0.112, size * 0.062
    cx = cy = size / 2

    layer = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(layer)
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
    # Inner cut-out leaves a constant-width band.
    d.ellipse((cx - rx + thick, cy - ry + thick, cx + rx - thick, cy + ry - thick), fill=0)

    if lower_half_only:
        keep = Image.new("L", (size, size), 0)
        ImageDraw.Draw(keep).rectangle((0, cy - ry * 0.15, size, size), fill=255)
        layer = Image.composite(layer, Image.new("L", (size, size), 0), keep)

    return layer.rotate(TILT, resample=Image.BICUBIC, center=(cx, cy))


def draw_master(size: int = S, *, tile: bool = True) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # --- tile ------------------------------------------------------------
    if tile:
        inset = round(size * 0.03)
        radius = round(size * 0.215)
        ImageDraw.Draw(img).rounded_rectangle(
            (inset, inset, size - inset, size - inset), radius=radius, fill=TILE + (255,)
        )

    # --- ring behind the planet, then planet, then the front of the ring --
    img.alpha_composite(Image.merge("RGBA", [Image.new("L", (size, size), c) for c in RING]
                                    + [ring_band(size, lower_half_only=False)]))

    cx = cy = size / 2
    pr = size * 0.232
    ImageDraw.Draw(img).ellipse((cx - pr, cy - pr, cx + pr, cy + pr), fill=PLANET + (255,))

    img.alpha_composite(Image.merge("RGBA", [Image.new("L", (size, size), c) for c in RING]
                                    + [ring_band(size, lower_half_only=True)]))

    # --- sparkle ---------------------------------------------------------
    ImageDraw.Draw(img).polygon(
        sparkle(size * 0.785, size * 0.235, size * 0.066, 0.28), fill=SPARKLE + (255,)
    )

    return img


def small_simplified(size: int) -> Image.Image:
    """A chunkier drawing for the 16-24 px frames.

    At that size the ring band and the sparkle collapse into noise, so the small
    frames thicken the ring, drop the sparkle and tighten the margins.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inset = round(size * 0.015)
    ImageDraw.Draw(img).rounded_rectangle(
        (inset, inset, size - inset, size - inset),
        radius=round(size * 0.22), fill=TILE + (255,),
    )
    cx = cy = size / 2
    pr = size * 0.255
    thick = max(1.5, size * 0.085)

    def band(lower_only: bool) -> Image.Image:
        rx, ry = size * 0.40, size * 0.135
        layer = Image.new("L", (size, size), 0)
        d = ImageDraw.Draw(layer)
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
        d.ellipse((cx - rx + thick, cy - ry + thick, cx + rx - thick, cy + ry - thick), fill=0)
        if lower_only:
            keep = Image.new("L", (size, size), 0)
            ImageDraw.Draw(keep).rectangle((0, cy - ry * 0.15, size, size), fill=255)
            layer = Image.composite(layer, Image.new("L", (size, size), 0), keep)
        return layer.rotate(TILT, resample=Image.BICUBIC, center=(cx, cy))

    img.alpha_composite(Image.merge("RGBA", [Image.new("L", (size, size), c) for c in RING] + [band(False)]))
    ImageDraw.Draw(img).ellipse((cx - pr, cy - pr, cx + pr, cy + pr), fill=PLANET + (255,))
    img.alpha_composite(Image.merge("RGBA", [Image.new("L", (size, size), c) for c in RING] + [band(True)]))
    return img


def build_ico(master: Image.Image, path: Path) -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = []
    for s in sizes:
        frames.append(small_simplified(s) if s <= 24 else master.resize((s, s), Image.LANCZOS))
    frames[-1].save(path, format="ICO", sizes=[(s, s) for s in sizes], bitmap_format="png")


def main() -> None:
    APP_RES.mkdir(parents=True, exist_ok=True)
    DOC_IMAGES.mkdir(parents=True, exist_ok=True)

    master = draw_master()
    mark = draw_master(tile=False)

    master.resize((512, 512), Image.LANCZOS).save(APP_RES / "astrohybrid.png", format="PNG", optimize=True)
    mark.resize((512, 512), Image.LANCZOS).save(APP_RES / "astrohybrid-mark.png", format="PNG", optimize=True)
    build_ico(master, APP_RES / "astrohybrid.ico")

    # Preview sheet: the mark large, then the sizes a Windows shell actually uses.
    preview = Image.new("RGBA", (1240, 520), (11, 14, 20, 255))
    preview.alpha_composite(master.resize((440, 440), Image.LANCZOS), (50, 40))
    preview.alpha_composite(mark.resize((300, 300), Image.LANCZOS), (540, 110))
    x, base = 880, 40 + 440
    for s in (128, 64, 48, 32, 24, 16):
        frame = small_simplified(s) if s <= 24 else master.resize((s, s), Image.LANCZOS)
        preview.alpha_composite(frame, (x, base - s))
        x += s + 18
    preview.save(DOC_IMAGES / "astrohybrid-logo.png", format="PNG", optimize=True)

    print("wrote", APP_RES / "astrohybrid.png")
    print("wrote", APP_RES / "astrohybrid-mark.png")
    print("wrote", APP_RES / "astrohybrid.ico")
    print("wrote", DOC_IMAGES / "astrohybrid-logo.png")


if __name__ == "__main__":
    main()
