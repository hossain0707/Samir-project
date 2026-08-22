"""Prepare deterministic desktop and report assets from the supplied CBDS logo."""

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageOps


def main(source: str, output_dir: str) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    image = Image.open(source).convert("RGBA")
    white = Image.new("RGBA", image.size, "white")
    difference = ImageChops.difference(image, white).convert("L")
    difference = difference.point(lambda p: 255 if p > 12 else 0)
    box = difference.getbbox() or (0, 0, image.width, image.height)
    logo = image.crop(box)

    display = ImageOps.contain(logo, (720, 360), Image.Resampling.LANCZOS)
    display.save(out / "cbds_logo.png", optimize=True)

    icon_canvas = Image.new("RGBA", (512, 512), "white")
    icon_logo = ImageOps.contain(logo, (454, 390), Image.Resampling.LANCZOS)
    icon_canvas.alpha_composite(icon_logo, ((512 - icon_logo.width) // 2, (512 - icon_logo.height) // 2))
    icon_canvas.save(out / "cbds.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    watermark = ImageEnhance.Contrast(display.convert("RGBA")).enhance(.72)
    watermark.putalpha(34)
    watermark.save(out / "cbds_watermark.png", optimize=True)
    print(f"Prepared CBDS brand assets in {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
