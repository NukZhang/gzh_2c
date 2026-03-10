import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import article_tools


def make_image_bytes(size=(120, 80), color=(60, 120, 180)):
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format="JPEG", quality=95)
    return output.getvalue()


def test_extract_article_image_urls_prefers_rich_pages_images():
    html = """
    <html>
      <body>
        <img src="https://mmbiz.qpic.cn/mmbiz_jpg/cover/0?wx_fmt=jpeg" alt="cover_image" />
        <img class="rich_pages wxw-img" data-src="https://mmbiz.qpic.cn/mmbiz_png/foo/640?wx_fmt=png&amp;from=appmsg" />
        <img class="other" data-src="https://mmbiz.qpic.cn/mmbiz_png/skip/640?wx_fmt=png&amp;from=appmsg" />
        <img class="rich_pages wxw-img" src="https://mmbiz.qpic.cn/mmbiz_jpg/bar/640?wx_fmt=jpeg&amp;from=appmsg" />
      </body>
    </html>
    """

    urls = article_tools.extract_article_image_urls(html)

    assert urls == [
        "https://mmbiz.qpic.cn/mmbiz_png/foo/640?wx_fmt=png&from=appmsg",
        "https://mmbiz.qpic.cn/mmbiz_jpg/bar/640?wx_fmt=jpeg&from=appmsg",
    ]


def test_process_article_images_returns_per_image_summary(tmp_path):
    raw_bytes = make_image_bytes()
    clean_bytes = make_image_bytes(color=(80, 140, 200))
    mask = np.zeros((80, 120), dtype=np.uint8)
    mask[-24:, -24:] = 255

    def fake_download(_url, session=None, timeout=20):
        return raw_bytes

    def fake_analyze(_image_bytes):
        return {
            "cleaned_bytes": clean_bytes,
            "mask": mask,
            "score": 0.81,
        }

    result = article_tools.process_article_images(
        ["https://example.com/1.jpg"],
        output_dir=tmp_path,
        save_images=True,
        download_image_fn=fake_download,
        analyze_image_fn=fake_analyze,
    )

    assert result["images"][0]["status"] == "processed"
    assert result["images"][0]["changed"] is True
    assert result["images"][0]["score"] == 0.81
    assert (tmp_path / "01_original.jpg").exists()
    assert (tmp_path / "01_mask.png").exists()
    assert (tmp_path / "01_clean.jpg").exists()
