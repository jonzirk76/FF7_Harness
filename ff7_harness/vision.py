"""Small image measurements; these do not infer game state on their own."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageChops, ImageStat


def dimensions(png: bytes) -> tuple[int, int]:
    with Image.open(BytesIO(png)) as image:
        return image.size


def pixel_change(before: bytes, after: bytes) -> float:
    """Mean absolute RGB change, 0..1, after resizing both frames to 128x128."""
    def normalize(raw: bytes) -> Image.Image:
        with Image.open(BytesIO(raw)) as image:
            resampling = getattr(Image, "Resampling", Image)
            return image.convert("RGB").resize((128, 128), resampling.BILINEAR)

    diff = ImageChops.difference(normalize(before), normalize(after))
    return sum(ImageStat.Stat(diff).mean) / (3 * 255)
