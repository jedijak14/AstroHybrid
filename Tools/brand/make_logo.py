#!/usr/bin/env python3
"""Generate the AstroHybrid app icon (PNG + multi-resolution ICO).

The mark is drawn from scratch: a rounded-square badge in the launcher's own
indigo/violet gradient carrying a four-point sparkle, with a thin amber orbit
ring and a small planet crossing it. Everything is supersampled so the curves
stay clean at 16 px.

Usage:
    python3 Tools/brand/make_logo.py
Writes:
    AstroHybrid.App/Resources/astrohybrid.png   (512 px, used by the UI)
    AstroHybrid.App/Resources/astrohybrid.ico   (16-256 px, window/exe icon)
    Docs/images/astrohybrid-logo.png            (documentation preview)
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
APP_RES = ROOT / "AstroHybrid.App" / "Resources"
DOC_IMAGES = ROOT / "Docs" / "images"

S = 2048  # master canvas (downscaled from here)

BADGE_TOP = (124, 106, 255)
BADGE_BOTTOM = (58, 34, 168)
GLOW = (168, 138, 255)
AMBER = (255, 196, 92)
WHITE = (255, 255, 255)


def vertical_gradient(size: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    grad = Image.new("RGB", (1, size))
    px = grad.load()
    for y in range(size):
        t = y / max(size - 1, 1)
        # Ease the ramp so the upper half stays lighter, like real lighting.
        t = t ** 0.85
        px[0, y] = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return grad.resize((size, size), Image.BILINEAR)


def sparkle(
    cx: float,
    cy: float,
    radius: float,
    waist: float,
    radius_y: float | None = None,
) -> list[tuple[float, float]]:
    """Four-point star with concave sides (waist = 0..1, smaller = sharper).

    radius_y scales the vertical points independently so the mark can be
    balanced (equal optical weight above and below) instead of elongated.
    """
    ry = radius if radius_y is None else radius_y
    pts: list[tuple[float, float]] = []
    for i in range(8):
        angle = -math.pi / 2 + i * math.pi / 4
        r = 1.0 if i % 2 == 0 else waist
        pts.append((cx + r * radius * math.cos(angle), cy + r * ry * math.sin(angle)))
    return pts


def draw_master(size: int = S) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # --- badge -----------------------------------------------------------
    inset = round(size * 0.045)
    radius = round(size * 0.225)
    box = (inset, inset, size - inset, size - inset)

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius=radius, fill=255)

    badge = vertical_gradient(size, BADGE_TOP, BADGE_BOTTOM).convert("RGBA")
    badge.putalpha(mask)
    img.alpha_composite(badge)

    # Soft light from the upper left, clipped to the badge.
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse(
        (
            -size * 0.15,
            -size * 0.35,
            size * 0.95,
            size * 0.72,
        ),
        fill=GLOW + (86,),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.09))
    glow.putalpha(Image.composite(glow.getchannel("A"), Image.new("L", (size, size), 0), mask))
    img.alpha_composite(glow)

    # Vignette towards the bottom right keeps the badge from looking flat.
    shade = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    sd.ellipse((size * 0.22, 0.42 * size, size * 1.30, size * 1.40), fill=(20, 9, 58, 104))
    shade = shade.filter(ImageFilter.GaussianBlur(size * 0.11))
    shade.putalpha(Image.composite(shade.getchannel("A"), Image.new("L", (size, size), 0), mask))
    img.alpha_composite(shade)

    # Inner rim light.
    rim = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim)
    rd.rounded_rectangle(box, radius=radius, outline=WHITE + (56,), width=max(2, round(size * 0.008)))
    rd.rounded_rectangle(
        (inset + size * 0.012, inset + size * 0.012, size - inset - size * 0.012, size - inset - size * 0.012),
        radius=round(radius * 0.94),
        outline=(255, 255, 255, 22),
        width=max(1, round(size * 0.003)),
    )
    img.alpha_composite(rim)

    # --- orbit -----------------------------------------------------------
    cx, cy = size * 0.5, size * 0.52
    orbit = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    od = ImageDraw.Draw(orbit)
    ring_r = size * 0.315
    ring_w = max(3, round(size * 0.014))
    od.ellipse(
        (cx - ring_r, cy - ring_r * 0.62, cx + ring_r, cy + ring_r * 0.62),
        outline=AMBER + (205,),
        width=ring_w,
    )
    # Fade the back half of the ring so it reads as passing behind the star.
    fade = Image.new("L", (size, size), 0)
    ImageDraw.Draw(fade).rectangle((0, 0, size, cy), fill=255)
    fade = fade.filter(ImageFilter.GaussianBlur(size * 0.02))
    orbit.putalpha(Image.composite(orbit.getchannel("A"), Image.new("L", (size, size), 64), fade))
    orbit = orbit.rotate(-16, resample=Image.BICUBIC, center=(cx, cy))
    img.alpha_composite(orbit)

    # --- sparkle ---------------------------------------------------------
    star = sparkle(cx, cy * 0.98, size * 0.315, 0.42, radius_y=size * 0.295)
    sdw = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(sdw).polygon(star, fill=(24, 10, 70, 120))
    sdw = sdw.filter(ImageFilter.GaussianBlur(size * 0.022)).transform(
        (size, size), Image.AFFINE, (1, 0, 0, 0, 1, -size * 0.012)
    )
    img.alpha_composite(sdw)
    ImageDraw.Draw(img).polygon(star, fill=WHITE + (255,))

    # A smaller companion sparkle, upper right, tucked behind the ring.
    mini = sparkle(size * 0.755, size * 0.275, size * 0.094, 0.38, radius_y=size * 0.088)
    ImageDraw.Draw(img).polygon(mini, fill=WHITE + (215,))

    return img


def build_ico(master: Image.Image, path: Path) -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [master.resize((s, s), Image.LANCZOS) for s in sizes]
    frames[-1].save(path, format="ICO", sizes=[(s, s) for s in sizes], bitmap_format="png")


def main() -> None:
    APP_RES.mkdir(parents=True, exist_ok=True)
    DOC_IMAGES.mkdir(parents=True, exist_ok=True)

    master = draw_master()

    png = master.resize((512, 512), Image.LANCZOS)
    png.save(APP_RES / "astrohybrid.png", format="PNG", optimize=True)

    build_ico(master, APP_RES / "astrohybrid.ico")

    preview = Image.new("RGBA", (1500, 600), (11, 14, 20, 255))
    preview.alpha_composite(master.resize((512, 512), Image.LANCZOS), (60, 44))
    for i, s in enumerate([256, 128, 64, 48, 32, 16]):
        x = 660 + sum([0] + [prev + 28 for prev in [256, 128, 64, 48, 32][:i]])
        preview.alpha_composite(master.resize((s, s), Image.LANCZOS), (x, 44 + 512 - s))
    preview.save(DOC_IMAGES / "astrohybrid-logo.png", format="PNG", optimize=True)

    print("wrote", APP_RES / "astrohybrid.png")
    print("wrote", APP_RES / "astrohybrid.ico")
    print("wrote", DOC_IMAGES / "astrohybrid-logo.png")


if __name__ == "__main__":
    main()
