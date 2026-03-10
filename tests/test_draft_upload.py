import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import draft_upload


def encode_image(image):
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=95)
    return output.getvalue()


def decode_image(image_bytes):
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


def create_base_image(size=(900, 600), color=(70, 120, 180)):
    return Image.new("RGB", size, color)


def add_watermark_overlay(image):
    watermark = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark)
    left = image.width - 210
    top = image.height - 92
    draw.rounded_rectangle(
        (left, top, image.width - 30, image.height - 30),
        radius=10,
        fill=(255, 255, 255, 185),
    )
    draw.text((left + 18, top + 24), "WATERMARK", fill=(55, 55, 55, 255))
    return Image.alpha_composite(image.convert("RGBA"), watermark).convert("RGB")


def roi_difference(left_image, right_image, roi_ratio=0.3):
    width, height = left_image.size
    roi = (
        int(width * (1 - roi_ratio)),
        int(height * (1 - roi_ratio)),
        width,
        height,
    )
    left = np.array(left_image.crop(roi), dtype=np.int16)
    right = np.array(right_image.crop(roi), dtype=np.int16)
    return np.abs(left - right).sum()


def test_remove_watermark_preserves_size_and_changes_watermarked_region():
    source = add_watermark_overlay(create_base_image())
    source_bytes = encode_image(source)

    cleaned_bytes = draft_upload.remove_watermark(source_bytes)
    cleaned = decode_image(cleaned_bytes)

    assert cleaned.size == source.size
    assert roi_difference(source, cleaned) > 0
