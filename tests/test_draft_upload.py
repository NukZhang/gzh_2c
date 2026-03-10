import io
import subprocess
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


def add_watermark_overlay(image, anchor="lower_right"):
    watermark = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark)
    if anchor == "lower_right":
        left = image.width - 210
        right = image.width - 30
    elif anchor == "lower_left":
        left = 30
        right = 210
    else:
        raise ValueError("unsupported anchor")

    top = image.height - 92
    draw.rounded_rectangle(
        (left, top, right, image.height - 30),
        radius=10,
        fill=(255, 255, 255, 185),
    )
    draw.text((left + 18, top + 24), "WATERMARK", fill=(55, 55, 55, 255))
    return Image.alpha_composite(image.convert("RGBA"), watermark).convert("RGB")


def add_qr_like_badge(image):
    draw = ImageDraw.Draw(image)
    badge_size = 108
    cell_size = 12
    left = image.width - badge_size - 28
    top = image.height - badge_size - 28

    for row in range(badge_size // cell_size):
        for col in range(badge_size // cell_size):
            color = (35, 35, 35) if (row + col) % 2 == 0 else (165, 165, 165)
            x0 = left + col * cell_size
            y0 = top + row * cell_size
            draw.rectangle((x0, y0, x0 + cell_size - 2, y0 + cell_size - 2), fill=color)

    draw.rectangle((left, top + badge_size - 16, left + badge_size, top + badge_size), fill=(25, 25, 25))
    return image


def add_caption_bar(image):
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    left = image.width - 320
    top = image.height - 104
    draw.rounded_rectangle(
        (left, top, image.width - 24, image.height - 24),
        radius=14,
        fill=(248, 248, 248, 220),
    )
    draw.rectangle((left + 18, top + 20, left + 86, top + 74), fill=(244, 163, 49, 255))
    draw.text((left + 104, top + 26), "CHART NOTE", fill=(45, 45, 45, 255))
    draw.text((left + 104, top + 56), "Q4 +18%", fill=(45, 45, 45, 255))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


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


def image_difference(left_image, right_image):
    left = np.array(left_image, dtype=np.int16)
    right = np.array(right_image, dtype=np.int16)
    return np.abs(left - right).sum()


def test_remove_watermark_preserves_size_and_changes_watermarked_region():
    source = add_watermark_overlay(create_base_image())
    source_bytes = encode_image(source)
    source_decoded = decode_image(source_bytes)

    cleaned_bytes = draft_upload.remove_watermark(source_bytes)
    cleaned = decode_image(cleaned_bytes)

    assert cleaned.size == source_decoded.size
    assert roi_difference(source_decoded, cleaned) > 0


def test_remove_watermark_cleans_qr_like_badge():
    source = add_qr_like_badge(create_base_image(color=(90, 135, 175)))
    source_bytes = encode_image(source)
    source_decoded = decode_image(source_bytes)

    cleaned_bytes = draft_upload.remove_watermark(source_bytes)
    cleaned = decode_image(cleaned_bytes)

    assert cleaned.size == source_decoded.size
    assert roi_difference(source_decoded, cleaned) > 5000


def test_remove_watermark_leaves_clean_image_unchanged():
    source = create_base_image(color=(96, 144, 188))
    source_bytes = encode_image(source)
    source_decoded = decode_image(source_bytes)

    cleaned_bytes = draft_upload.remove_watermark(source_bytes)
    cleaned = decode_image(cleaned_bytes)

    assert cleaned.size == source_decoded.size
    assert image_difference(source_decoded, cleaned) == 0


def test_remove_watermark_does_not_destroy_legitimate_lower_right_content():
    source = add_caption_bar(create_base_image(color=(70, 112, 176)))
    source_bytes = encode_image(source)
    source_decoded = decode_image(source_bytes)

    cleaned_bytes = draft_upload.remove_watermark(source_bytes)
    cleaned = decode_image(cleaned_bytes)

    assert cleaned.size == source_decoded.size
    assert image_difference(source_decoded, cleaned) == 0


def test_detect_watermark_mask_only_flags_lower_right_candidates():
    positive = add_watermark_overlay(create_base_image())
    negative = add_watermark_overlay(create_base_image(), anchor="lower_left")

    positive_mask, _, positive_score = draft_upload.detect_watermark_mask(
        draft_upload.load_image_array(encode_image(positive))
    )
    negative_mask, _, negative_score = draft_upload.detect_watermark_mask(
        draft_upload.load_image_array(encode_image(negative))
    )

    assert np.count_nonzero(positive_mask) > 0
    assert positive_score >= 0.6
    assert np.count_nonzero(negative_mask) == 0
    assert negative_score == 0.0


def test_remove_watermark_writes_debug_artifacts_when_enabled(tmp_path, monkeypatch):
    source = add_watermark_overlay(create_base_image())
    source_bytes = encode_image(source)

    monkeypatch.setenv("WATERMARK_DEBUG", "1")
    monkeypatch.setenv("WATERMARK_DEBUG_DIR", str(tmp_path))

    draft_upload.remove_watermark(source_bytes)

    assert (tmp_path / "debug_original.jpg").exists()
    assert (tmp_path / "debug_mask.png").exists()
    assert (tmp_path / "debug_clean.jpg").exists()


def test_detect_watermark_mask_does_not_crash_on_bright_banner():
    script = """
import io
import sys
from PIL import Image
sys.path.insert(0, 'src')
import draft_upload

img = Image.new('RGB', (1080, 360), (255, 255, 255))
buf = io.BytesIO()
img.save(buf, format='JPEG', quality=95)
image_bgr = draft_upload.load_image_array(buf.getvalue())
mask, roi_bounds, score = draft_upload.detect_watermark_mask(image_bgr)
print(mask.shape, roi_bounds, score)
"""
    result = subprocess.run(
        [sys.executable, "-u", "-c", script],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
