#!/usr/bin/env python3
"""Render versioned brand assets from the UI SVG (Pillow and ImageMagick)."""

from io import BytesIO
from pathlib import Path
import subprocess

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "apps/web/src/components/brandMark.svg"
OUTPUT = ROOT / "apps/web/public/brand/v2"
DARK_ACCENT = "#32e0e0"
LIGHT_ACCENT = "#007c8b"
BACKGROUND = "#082938"


def svg(color: str) -> str:
    return SOURCE.read_text().replace('stroke="currentColor"', f'stroke="{color}"')


def render(width: int, color: str = DARK_ACCENT) -> Image.Image:
    height = round(width * 72 / 128)
    source = svg(color).replace('<svg ', f'<svg width="{width * 4}" height="{height * 4}" ', 1)
    result = subprocess.run(
        ["convert", "-background", "none", "svg:-", "png:-"],
        input=source.encode(), capture_output=True, check=True,
    )
    return Image.open(BytesIO(result.stdout)).convert("RGBA").resize(
        (width, height), Image.Resampling.LANCZOS,
    )


def icon(size: int, *, maskable: bool = False, transparent: bool = False) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0) if transparent else BACKGROUND)
    mark = render(round(size * (0.60 if maskable else 0.82)))
    image.alpha_composite(mark, ((size - mark.width) // 2, (size - mark.height) // 2))
    return image


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "logo-dark.svg").write_text(svg(DARK_ACCENT) + "\n")
    (OUTPUT / "logo-light.svg").write_text(svg(LIGHT_ACCENT) + "\n")
    favicon = svg(LIGHT_ACCENT).replace(
        "><path", "><style>@media(prefers-color-scheme:dark){svg{stroke:#32e0e0}}</style><path", 1,
    )
    (OUTPUT / "favicon.svg").write_text(favicon + "\n")
    for size in (16, 32, 48):
        icon(size, transparent=True).save(OUTPUT / f"favicon-{size}.png")
    icon(256, transparent=True).save(
        OUTPUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)],
    )
    icon(180).save(OUTPUT / "apple-touch-icon.png")
    for size in (192, 512):
        icon(size).save(OUTPUT / f"pwa-{size}.png")
    icon(512, maskable=True).save(OUTPUT / "pwa-maskable-512.png")
    social = Image.new("RGBA", (1200, 630), BACKGROUND)
    mark = render(680)
    social.alpha_composite(mark, ((1200 - mark.width) // 2, (630 - mark.height) // 2))
    social.convert("RGB").save(OUTPUT / "social-share-1200x630.png")


if __name__ == "__main__":
    main()
