#!/usr/bin/env python3
"""Derive browser icons from the supplied PNG, preserving its aspect ratio."""

from pathlib import Path

from PIL import Image, ImageOps


PUBLIC = Path(__file__).resolve().parents[1] / "apps/web/public"
SOURCE = PUBLIC / "brand/hawatch-favicon-512.png"


def square(source: Image.Image, size: int) -> Image.Image:
    mark = ImageOps.contain(source, (size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(mark, ((size - mark.width) // 2, (size - mark.height) // 2))
    return canvas


def main() -> None:
    with Image.open(SOURCE) as image:
        source = ImageOps.exif_transpose(image).convert("RGBA")
        square(source, 96).save(PUBLIC / "favicon.png")
        square(source, 180).save(PUBLIC / "apple-touch-icon.png")
        square(source, 256).save(
            PUBLIC / "favicon.ico", format="ICO",
            sizes=[(16, 16), (32, 32), (48, 48), (96, 96), (256, 256)],
        )


if __name__ == "__main__":
    main()
